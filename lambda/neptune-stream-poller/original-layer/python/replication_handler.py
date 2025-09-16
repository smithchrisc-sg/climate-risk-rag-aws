import abc
import six
import logging
from commons import *
from handler import HandlerResponse
from config_provider import config_provider
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# Logger
logger = logging.getLogger(__name__)
logger.setLevel(config_provider.logging_level)

TARGET_WRITE_WORKER_POOL_SIZE = int(config_provider.get_handler_additional_param('TargetWriteWorkerPoolSize', '1'))
REPLICATION_MODE = config_provider.get_handler_additional_param('ReplicationMode', 'Legacy')
LOW_NUMBER_OF_PARALLEL_WORKERS = 1

"""
Abstract class to Replicate Stream Records to a target Neptune cluster or ES domain
"""

@six.add_metaclass(abc.ABCMeta)
class ReplicationHandler:

    def handle_records(self, stream_log, query_queue):

        """
        Handles Stream records. This method is called from Lambda Function to process records.
        This method perform below steps sequentially :
        1) Build Gremlin/Sparql Queries from Stream records
        2) Batch Multiple queries by grouping them based on their graph partition or same operation
        3) Queries are joined for Neptune to Neptune case and records are filtered and aggregated for Neptune to ES case
        4) Push the batched queries to a thread safe queue
        5) Yield HandlerResponse with last read checkpoint

        :param stream_log: Neptune Stream Change log
        :param query_queue: Thread safe queue
        """

        logger.info("Starting Neptune data replication !!!")
        records = stream_log[RECORDS_STR]
        lastTransactionTimeStamp = stream_log[LAST_TXN_TIMESTAMP_STR]
        totalRecords = stream_log[TOTAL_RECORDS]
        handler_name = config_provider.stream_records_handler_name

        # Default mode for gremlin is Transaction
        if REPLICATION_MODE == 'Transaction' and handler_name in [NEPTUNE_TO_NEPTUNE_GREMLIN, NEPTUNE_TO_ES_GREMLIN]:
            return self.__handle_records_transaction__(records, lastTransactionTimeStamp, query_queue)
        elif REPLICATION_MODE == 'Legacy': # Legacy is optional mode
            return self.__handle_records_legacy__(records, lastTransactionTimeStamp, totalRecords, query_queue)
        else: # Default mode for SPARQL is batch
            return self.__handle_records_batch__(records, lastTransactionTimeStamp, query_queue)

    def __handle_records_transaction__(self, records, lastTransactionTimeStamp, query_queue):
        if not records:
            return

        graph = {}
        edgeToVertexMap = {}

        # Create dependency graph using the records of edge addition/deletion
        # For Stream Record: Add E1 between V1 and V2, a graph G1 between V1 and V2 will be created
        # New Stream Record: Add E2 between V2 and V3, here V3 will be added in G1
        # New Stream Record: Add E3 between V4 and V5, a graph G2 between V4 and V5 will be created
        # Graph G1 and G2 will be independent of each other and can be written separately to target
        for record in records:
            operation = self.get_query_operation(record)
            if operation in [ADD_E, REMOVE_E]:
                record_data = record[DATA_STR]
                id = record_data[ID_STR]
                fromV = record_data[FROM_VERTEX_STR]
                toV = record_data[TO_VERTEX_STR]
                # Link edge to first vertex, so that it gets same batch id as vertex
                edgeToVertexMap[id] = fromV
                if not graph.get(fromV):
                    graph[fromV] = []
                graph[fromV].append(toV)
                if not graph.get(toV):
                    graph[toV] = []
                graph[toV].append(fromV)

        batchIdMap = {}
        currentBatchId = 1

        # Find all graph partitions in the created graph using DFS
        for vertexId in graph:
            if not batchIdMap.get(vertexId): # Vertex is not traversed yet
                self.__dfs__(graph, batchIdMap, vertexId, currentBatchId) # Traverse the vertex and linked vertices
                currentBatchId += 1

        batch_records = {}
        unbatch_records = []
        count = 0
        # Separate all records by graph partitions and independent records separately
        for record in records:
            operation = self.get_query_operation(record)
            record_data = record[DATA_STR]
            id = record_data[ID_STR]
            if operation in [ADD_E, REMOVE_E, ADD_EP, REMOVE_EP] and id in edgeToVertexMap:
                id = edgeToVertexMap[id]
            batchId = batchIdMap.get(id)
            if not batchId:
                unbatch_records.append(record)
            else:
                batchId = batchId % self.get_target_write_worker_pool_size()
                if not batch_records.get(batchId):
                    batch_records[batchId] = []
                batch_records[batchId].append(record)
                count += 1

        # Create batches of all independent records by batching them by operation
        if unbatch_records: # Batch all records not part of any sub-graph by operation to execute them in parallel
            yield from self.__handle_records_batch__(unbatch_records, lastTransactionTimeStamp, query_queue)

        batch_query_list = []
        for batchId in batch_records:
            record_list = batch_records.get(batchId)
            if record_list:
                batch_query = self.__create_batch_query__(record_list, lastTransactionTimeStamp)
                if batch_query:
                    batch_query_list.append(batch_query)

        # Push all graph partition records in shared queue to execute them in parallel
        if batch_query_list:
            last_record = records[-1]
            yield HandlerResponse(last_record[EVENT_ID_STR][OP_NUM_STR], last_record[EVENT_ID_STR][COMMIT_NUM_STR], count, lastTransactionTimeStamp)
            query_queue.put(QueryQueueModel(batch_query_list, last_record[EVENT_ID_STR][COMMIT_NUM_STR], last_record[EVENT_ID_STR][OP_NUM_STR])) # Push all batched sub-graphs in queue to execute them in parallel

    def __handle_records_legacy__(self, records, lastTransactionTimeStamp, totalRecords, query_queue):
        handler_name = config_provider.stream_records_handler_name
        batch_query_list = self.__create_batch_query_with_target_batch_size__(records, lastTransactionTimeStamp)
        if batch_query_list:
            for batch_query in batch_query_list: # Put in queue one by one for writing them one after another without batching
                query_queue.put(QueryQueueModel([batch_query]))
        last_record = records[-1]
        yield HandlerResponse(last_record[EVENT_ID_STR][OP_NUM_STR], last_record[EVENT_ID_STR][COMMIT_NUM_STR], totalRecords, lastTransactionTimeStamp)

    def __handle_records_batch__(self, records, lastTransactionTimeStamp, query_queue):
        group_operation_record_list = []
        property_group_operation_record_list = []
        count = 0
        group_operation = ''
        property_group_operation = ''
        last_record = None
        if records:
            group_operation, property_group_operation = self.__find_group_operation__(records[0])
            last_record = records[0]

        for record in records:
            count += 1
            operation = self.get_query_operation(record)
            if operation == group_operation:
                group_operation_record_list.append(record)
            elif operation == property_group_operation:
                property_group_operation_record_list.append(record)
            else:
                self.__create_batch_and_put_in_queue__(group_operation, property_group_operation, group_operation_record_list, property_group_operation_record_list, query_queue, lastTransactionTimeStamp)
                yield HandlerResponse(last_record[EVENT_ID_STR][OP_NUM_STR], last_record[EVENT_ID_STR][COMMIT_NUM_STR], count, lastTransactionTimeStamp)

                group_operation_record_list = []
                property_group_operation_record_list = []
                group_operation, property_group_operation = self.__find_group_operation__(record)
                count = 1

                if operation == group_operation:
                    group_operation_record_list.append(record)
                elif operation == property_group_operation:
                    property_group_operation_record_list.append(record)

            last_record = record

        if group_operation_record_list or property_group_operation_record_list:
            self.__create_batch_and_put_in_queue__(group_operation, property_group_operation, group_operation_record_list, property_group_operation_record_list, query_queue, lastTransactionTimeStamp)
            yield HandlerResponse(last_record[EVENT_ID_STR][OP_NUM_STR], last_record[EVENT_ID_STR][COMMIT_NUM_STR], count, lastTransactionTimeStamp)

    def __find_group_operation__(self, record):
        group_operation = self.get_query_operation(record)
        if group_operation in [ADD_VL, ADD_VP]:
            return ADD_VL, ADD_VP
        elif group_operation in [ADD_E, ADD_EP]:
            return ADD_E, ADD_EP
        elif group_operation in [REMOVE_VL, REMOVE_VP]:
            return REMOVE_VL, REMOVE_VP
        elif group_operation in [REMOVE_E, REMOVE_EP]:
            return REMOVE_E, REMOVE_EP
        elif group_operation in [ADD_OPERATION]:
            return ADD_OPERATION, ''
        elif group_operation in [REMOVE_OPERATION]:
            return REMOVE_OPERATION, ''

    def __create_batch_and_put_in_queue__(self, group_operation, property_group_operation, group_operation_record_list, property_group_operation_record_list, query_queue, lastTransactionTimeStamp):
        if self.__is_remove_operation__(group_operation):
            if property_group_operation_record_list:
                query_queue.put(QueryQueueModel(self.__create_batch_query_with_target_batch_size__(property_group_operation_record_list, lastTransactionTimeStamp)))
            if group_operation_record_list:
                query_queue.put(QueryQueueModel(self.__create_batch_query_with_target_batch_size__(group_operation_record_list, lastTransactionTimeStamp)))
        else:
            if group_operation_record_list:
                query_queue.put(QueryQueueModel(self.__create_batch_query_with_target_batch_size__(group_operation_record_list, lastTransactionTimeStamp)))
            if property_group_operation_record_list:
                query_queue.put(QueryQueueModel(self.__create_batch_query_with_target_batch_size__(property_group_operation_record_list, lastTransactionTimeStamp)))

    def __is_remove_operation__(self, group_operation):
        if group_operation in [REMOVE_VL, REMOVE_E, REMOVE_OPERATION]:
            return True
        return False

    def __dfs__(self, graph, batchIdMap, id, currentBatchId):
        batchIdMap[id] = currentBatchId
        dependency_list = graph.get(id)
        if dependency_list:
            for vertexId in dependency_list:
                if not batchIdMap.get(vertexId):
                    self.__dfs__(graph, batchIdMap, vertexId, currentBatchId)

    def __create_batch_query__(self, record_list, lastTransactionTimeStamp):
        handler_name = config_provider.stream_records_handler_name
        batch_query_list = []
        query = []
        count = 0
        batch_query = ''

        for record in record_list:
            count += 1
            if handler_name in [NEPTUNE_TO_NEPTUNE_GREMLIN, NEPTUNE_TO_NEPTUNE_SPARQL]:
                query.append(self.build_query(record))
            else:
                query.append(record)

        if query:
            curr_event_id = "{}:{}".format(record[EVENT_ID_STR][COMMIT_NUM_STR], record[EVENT_ID_STR][OP_NUM_STR])
            batch_query = self.__get_batch_query__(query, handler_name)
            return [batch_query, curr_event_id, count, lastTransactionTimeStamp]

        return []

    def __create_batch_query_with_target_batch_size__(self, group_operation_record_list, lastTransactionTimeStamp):
        handler_name = config_provider.stream_records_handler_name
        batch_query_list = []
        query = []
        count = 0
        batch_query = ''

        for record in group_operation_record_list:
            count += 1
            if handler_name in [NEPTUNE_TO_NEPTUNE_GREMLIN, NEPTUNE_TO_NEPTUNE_SPARQL]:
                query.append(self.build_query(record))
            else:
                query.append(record)

            if query and count % self.get_target_write_batch_size() == 0:
                curr_event_id = "{}:{}".format(record[EVENT_ID_STR][COMMIT_NUM_STR], record[EVENT_ID_STR][OP_NUM_STR])
                batch_query = self.__get_batch_query__(query, handler_name)
                batch_query_list.append([batch_query, curr_event_id, self.get_target_write_batch_size(), lastTransactionTimeStamp])
                query = []

        if query:
            curr_event_id = "{}:{}".format(record[EVENT_ID_STR][COMMIT_NUM_STR], record[EVENT_ID_STR][OP_NUM_STR])
            batch_query = self.__get_batch_query__(query, handler_name)
            batch_query_list.append([batch_query, curr_event_id, count % self.get_target_write_batch_size(), lastTransactionTimeStamp])

        return batch_query_list

    def __get_batch_query__(self, query, handler_name):
        if handler_name in [NEPTUNE_TO_NEPTUNE_GREMLIN, NEPTUNE_TO_NEPTUNE_SPARQL]:
            return query
        else:
            filter_records = self.filter_records(query, self.get_es_client())
            return self.generate_aggregated_es_actions(filter_records)

    def write_records(self, query_queue_model):

        """
        Writes batched queries. This method is called from Lambda Function to write batched queries.

        This method writes all batched queries from batch_query_list from query_queue_model to target Neptune cluster
        or ES domain in parallel depending on the TARGET_WRITE_WORKER_POOL_SIZE

        :param query_queue_model: Contains a list of batched queries and optional commit-num and op-num
        """

        batch_count = 0

        for batch_query in query_queue_model.batch_query_list:
            batch_count += batch_query[2]

        parallel_queries_count = len(query_queue_model.batch_query_list)
        parallel_workers_count = min(parallel_queries_count, self.get_target_write_worker_pool_size())
        batch_size = self.get_target_write_batch_size()
        if parallel_workers_count <= LOW_NUMBER_OF_PARALLEL_WORKERS:
            batch_size = self.get_max_target_write_batch_size()
        logger.info("Executing {} batch queries with batch size {} in parallel using {} workers".format(parallel_queries_count, batch_size, parallel_workers_count))

        try:
            with ThreadPoolExecutor(max_workers=parallel_queries_count) as executor:
                futures = {executor.submit(self.__run_query__, batch_query, batch_size) : batch_query for batch_query in query_queue_model.batch_query_list}
                for future in as_completed(futures):
                    future.result() # Need to call result() so that exception can be raised
            logger.info("Batch queries executed successfully")
        except Exception as e:
            raise e # Raise exception to avoid updating checkpoint in case of write failure

        last_commit_num = 0
        last_op_num = 0
        if query_queue_model.last_commit_num > 0:
            last_commit_num = query_queue_model.last_commit_num
            last_op_num = query_queue_model.last_op_num
        else:
            batch_query = query_queue_model.batch_query_list[-1]
            event_id_split = batch_query[1].split(':')
            last_commit_num = event_id_split[0]
            last_op_num = event_id_split[1]
        return HandlerResponse(last_op_num, last_commit_num, batch_count, batch_query[3])

    def __run_query__(self, batch_query, batch_size):
        try:
            logger.info("Executing batch query for Stream record set with last event id (commitNum:OpNum) - {}"
                .format(batch_query[1]))
            logger.debug("Batch Query - {}".format(batch_query[0]))
            self.execute_query(batch_query[0], batch_size)

        except Exception as e:
            handler = config_provider.stream_records_handler_name
            if handler in [NEPTUNE_TO_NEPTUNE_GREMLIN, NEPTUNE_TO_NEPTUNE_SPARQL]:
                logger.error("Error Occurred - {}  while running query {} on Neptune host:port {} "
                    .format(str(e), batch_query[0], config_provider.get_handler_additional_param('NeptuneCluster', '')))
            else:
                ES_ENDPOINT = es_helper.get_url_components(config_provider.get_handler_additional_param('ElasticSearchEndpoint'))
                logger.error("Error Occurred - {}  while doing bulk update to Elastic Search endpoint {}:{} "
                    .format(str(e), self.get_es_endpoint_host(), self.get_es_endpoint_port()))
            raise e

    def get_target_write_worker_pool_size(self):
        return TARGET_WRITE_WORKER_POOL_SIZE

class QueryQueueModel:

    """
    Model for Storing data in Query Queue.

    last_op_num - Op_num for last stream record processed
    last_commit_num - Commit number for last stream record processed
    records_processed - Number of Stream Records Processed
    last_transaction_time_stamp - Time stamp of last transaction (Optional parameter)
    """

    def __init__(self, batch_query_list, last_commit_num=0, last_op_num=0):
        self.batch_query_list = batch_query_list
        self.last_commit_num = last_commit_num
        self.last_op_num = last_op_num