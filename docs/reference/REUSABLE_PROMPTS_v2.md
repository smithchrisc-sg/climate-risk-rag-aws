# Reusable Prompts for Project Documentation
## Created: 2025-07-05T00:25:00Z
## Updated: 2025-07-07T14:00:00Z - Added Git Workflow

## 📋 **Context Summary Creation Prompt**

Use this prompt to request comprehensive project context documentation:

---

**PROMPT:**

Please create a PROJECT_CONTEXT_SUMMARY document named with a timestamp as in the other project context documents in the docs/status directory. Make sure it includes all the necessary information to bring you up to speed if we need to start a fresh conversation. Be sure to reference existing work folders such as cdk, lambda, and layers so that context is not lost. Also add a section on being careful with expense when running tests so that we are not charged excessively for test runs. This is important for textract and will be important for comprehend usage and perhaps other services such as titan for embeddings generation. Reference work summary docs as well so they become part of the context.

Also create a NEXT_STEPS document, similarly timestamped to outline what we'll do next.

---

## 📚 **Session Onboarding Prompt**

Use this prompt to quickly bring a new AI session up to speed on the project:

---

**PROMPT:**

I need you to get up to speed on our Climate Risk RAG system project. Please read and analyze the following documents to understand the current state of our work:

**REQUIRED READING (in order):**

1. **Latest PROJECT_CONTEXT_SUMMARY**: Look in `/Users/chris/climate-risk-rag-aws/docs/status` for the most recent `PROJECT_CONTEXT_SUMMARY_YYYY-MM-DDTHH-MM-SSZ.md` file. This contains the complete project overview, architecture, current status, and cost management guidelines.

2. **Latest NEXT_STEPS**: Look for the most recent `NEXT_STEPS_YYYY-MM-DDTHH-MM-SSZ.md` file in the same directory. This outlines our immediate priorities and planned work.

3. **Recent Work Summaries**: Review the most recent 3-5 work summary documents in the docs directory to understand what has been completed recently.

**PROJECT STRUCTURE TO UNDERSTAND:**

- **Target system Root Directory**: `/Users/chris/climate-risk-rag-aws/` - This is what we're building together and should be the latest versions of everything
- **Key Folders**: 
  - `cdk/`: AWS infrastructure as code
  - `lambda/`: Lambda function source code (17+ functions)
  - `layers/`: Shared dependencies and utilities
  - `docs/`: Project documentation and context
    - `status/`: Project status tracking, context summaries, and next steps
    - `architecture/`: High-level system architecture, data flow, and messaging design
    - `design/`: Detailed component design documents and technical specifications
    - `integration/`: Integration plans for connecting different system components
    - `migration/`: POC to AWS migration guides and porting documentation
    - `deployment/`: CDK deployment guides, infrastructure setup, and deployment procedures
    - `implementation/`: Component implementation summaries and completion status
    - `testing/`: Testing strategies, guides, and test results
    - `reference/`: Reference materials, reusable content, and utility documentation
  - `database/`: Database schemas

**ORIGINAL POC CODE AND ASSETS:**
- **Root Directory**: `/Volumes/G-RAID\ Photo\ 24TB/climate_risk_rag/`
- **Key Folders**: 
  - `src/`: Source Code for standalone POC
  - `ontology/`: Various ontology files - work in progress, but provides an example of the concept
  - `doc/`: Architecture documentation with the philosophy behind what we're building
  - `db/`: Actual local database, sqlite, fuseki. Note that Qdrant and OpenSearch can be run locally - ask if you need them launched so that you can access them
  - `scripts/`: various run scripts - unfortunately not cleaned up, so there's some redundancy

**GIT REPOSITORY STATUS:**
- **Repository Initialized**: The project is now under Git version control
- **Current Version**: v1.1.0 (Vector Embeddings Pipeline Complete)
- **Branch**: main (production-ready code)
- **Initial Commit**: Complete system with 228 files committed
- **Next Milestone**: v1.2.0 (NLP Integration)

**IMPORTANT: I handle all Git mechanics** - The user prefers not to deal with Git commands directly. I should:
- Create feature branches for new development
- Commit incrementally as we build components
- Use clear, descriptive commit messages following conventional format
- Merge to main and tag milestones when complete
- Handle all branching, merging, and version control workflow

**GIT WORKFLOW PHILOSOPHY:**
Note direction in the list below. We should always use git to manage things. So, we don't want to create things like textract_processor.py, textract_processor_updated.py, textract_processor_fixed.py, etc. Just keep it as textract_processor.py with useful commit messages and tagging where we have working versions - we'll allow git to manage reverting to previous where needed. I don't want a proliferation of variously named revisions of any code, even run and test scripts - it just gets too confusing.
- **Milestone-based development** with tagged releases
- **Feature branches** for safe experimentation
- **Incremental commits** to track progress
- **Professional commit messages** with clear descriptions
- **User focuses on technical work** while I manage version control

**COST MANAGEMENT CRITICAL:**
- **AWS Services with high costs**: Textract (~$1.50/1000 pages), Bedrock Titan (~$0.002/doc), Comprehend (~$0.019/doc)
- **Testing limits**: Small batches (5-10 docs) for development, larger batches only after validation
- **Budget monitoring**: Daily alerts and cost tracking implemented
- **Production targets**: <$500/month operational costs for 1000 docs/day

**CURRENT SYSTEM STATUS:**
- ✅ **Text Extraction Pipeline** - Amazon Textract integration complete
- ✅ **Text Chunking Pipeline** - Structured chunking with metadata operational
- ✅ **Vector Embeddings Pipeline** - Amazon Bedrock Titan integration PRODUCTION READY
- ✅ **Database Integration** - PostgreSQL with complete schema
- ✅ **OpenSearch Integration** - VECTORSEARCH collection operational
- ✅ **CDK Infrastructure** - Automated deployment ready
- 🔄 **NLP Integration** - Next priority (entity detection & key phrases)

**PERFORMANCE METRICS ACHIEVED:**
- Vector processing: 4.6 seconds per document (19 chunks)
- Cost per document: $0.002187 (vector embeddings)
- Success rate: 100% in testing
- Daily capacity: 1,000+ documents

**CRITICAL CONTEXT:**

- This is an AWS serverless climate risk document processing system
- We use DocumentIDManager for proper GUID-based document identification
- All relational database access should be through DatabaseManager
- Lambda layers should continue to be the logical deployment scenario for shared functionality. (Check out LAMBDA_LAYER_DESIGN_UPDATED.md in the docs directory)
- Assume existing code is correct and do not make major changes, delete existing functions, or change method signatures without providing an explicit justification, the implications and impact (e.g., required refactoring), and then asking permission.
- Cost management is critical - especially for Textract, Comprehend, and Bedrock services
- We have 1,000 POC documents already migrated and integrated
- The system uses microservices architecture with async processing
- Work should be done using the AWS CLI with the solve-global configuration ensuring that we're in us-east-1
- In all cases, when changes are made, new configurations, schemas, or code are created, it is necessary to get the CDK code updated such that we could always build and deploy a working system from a clean slate.
- When developing code, such as porting to a lambda function or set of functions, 
    1. create and run a complete set of unit tests, 
    2. after unit tests are successful, deploy the infrastructure
    3. perform integration testing (mindful of frugality)
      a. first from the trigger messaging from the previous stage
      b. then from the full pipeline path available so far 
- DO NOT UNDER ANY CIRCUMSTANCE USE ACCOUNT NUMBER 614290363854. Check to be sure we are using the correct solve-global profile anytime we're doing anything that involves an account number - suchas creating ARNs

**CURRENT STATUS:**
- Available in PROJECT CONTEXT SUMMARY and NEXT STEPS documents as specified above

After reading these documents, please confirm your understanding of:
1. The current project status and architecture
2. What components are complete vs. in progress
3. The immediate next steps and priorities
4. Cost management requirements and testing protocols
5. Git workflow expectations and version control approach
6. The correct account and aws CLI configuration

Then ask what specific work we should focus on next.

---

## 🔄 **Quick Status Update Prompt**

Use this prompt to get a quick status update and next actions:

---

**PROMPT:**

Please provide a quick status update on our Climate Risk RAG system project:

1. **Current Status**: What major components are working and what needs attention?
2. **Immediate Priorities**: What should we work on next?
3. **Cost Considerations**: Any expense warnings for upcoming work?
4. **Blockers**: Anything preventing progress on key priorities?

Base your response on the latest PROJECT_CONTEXT_SUMMARY and NEXT_STEPS documents in the docs directory.

---

## 🧪 **Testing Guidance Prompt**

Use this prompt to get testing recommendations with cost awareness:

---

**PROMPT:**

I want to test [SPECIFIC COMPONENT/FEATURE]. Please provide testing recommendations that:

1. **Minimize Costs**: Especially for Textract, Comprehend, and Bedrock services
2. **Use Existing Data**: Leverage already processed documents when possible
3. **Start Small**: Use minimal test cases to validate functionality
4. **Monitor Usage**: Include cost tracking recommendations
5. **Validate Properly**: Ensure tests cover key integration points

Consider our current system status and the cost management guidelines in the latest PROJECT_CONTEXT_SUMMARY document.

---

## 📝 **Documentation Update Prompt**

Use this prompt to request documentation updates:

---

**PROMPT:**

Please update our project documentation to reflect recent work:

1. **Update PROJECT_CONTEXT_SUMMARY**: Create new timestamped version with current status
2. **Update NEXT_STEPS**: Reflect completed work and new priorities  
3. **Create Work Summary**: Document what was accomplished in this session
4. **Update Cost Guidelines**: Include any new cost considerations discovered
5. **Update Production Architecture Document**: Update to reflect current state as built.

Make sure all documents reference the key project folders (cdk, lambda, layers) and maintain continuity with existing documentation patterns.

---

## 🔧 **Deployment Assistance Prompt**

Use this prompt to get deployment help:

---

**PROMPT:**

I need help deploying [SPECIFIC COMPONENT]. Please:

1. **Check Current State**: Review existing deployment scripts and infrastructure
2. **Create/Update Deployment Script**: Ensure proper backup and rollback procedures
3. **Validate Configuration**: Check environment variables and dependencies
4. **Test Deployment**: Create validation scripts to verify successful deployment
5. **Document Changes**: Update relevant documentation

Consider the existing CDK infrastructure in the `cdk/` directory and Lambda functions in the `lambda/` directory. Ensure compatibility with our DocumentIDManager integration and cost management practices.

---

## 🔧 **Code Cleanup Prompt**

Use this prompt to cleanup code files:

---

**PROMPT:**

I need help cleaning up the proliferation of python code including test scripts, lambdas, CDK, etc.

1. **Review the existing python code**: Review existing scripts, cdk, lambda, etc.
2. **Cleanup the cruft**: Review and save only the latest working versions. Do not use naming like deploy_xyz.py, deploy_xyz_updated.py, deploy_xyz_fixed.py. Keep only the relevant files, named with the base descriptive name e.g., deploy_xyz.py, textract_processor.py, etc.
3. **GIT is your friend**: Use git to manage versions and changes. If there are multiple versions in the future, you'll want to keep the same name, but make sure all development versions are committed - don't go overboard - we shouldn't commit code with syntax errors, etc. but every working version should be committed to allow for us to revert where necessary. 
4. **Don't break things**: If the latest version is textract_processor_updated.py and we change that to the root name, be sure that any and all deployment scripts, cdk code, etc. is update to reflect the name.
5. **Document Changes**: Update relevant documentation

Here's the git philosophy as a reminder:

**GIT WORKFLOW PHILOSOPHY:**
Note direction in the list below. We should always use git to manage things. So, we don't want to create things like textract_processor.py, textract_processor_updated.py, textract_processor_fixed.py, etc. Just keep it as textract_processor.py with useful commit messages and tagging where we have working versions - we'll allow git to manage reverting to previous where needed. I don't want a proliferation of variously named revisions of any code, even run and test scripts - it just gets too confusing.
- **Milestone-based development** with tagged releases
- **Feature branches** for safe experimentation
- **Incremental commits** to track progress
- **Professional commit messages** with clear descriptions
- **User focuses on technical work** while I manage version control

---

## 💡 **Usage Notes**

### **When to Use Each Prompt**

- **Context Summary Creation**: End of major work sessions or milestones
- **Session Onboarding**: Start of new conversations or when bringing in new team members
- **Quick Status Update**: Beginning of work sessions to get oriented
- **Testing Guidance**: Before running any tests that might incur costs
- **Documentation Update**: After completing significant work
- **Deployment Assistance**: When deploying new or updated components
- **Code Cleanup**: When managing code organization and version control

### **Customization Tips**

- Replace `[SPECIFIC COMPONENT/FEATURE]` with actual component names
- Adjust cost considerations based on current AWS service usage
- Update file paths if project structure changes
- Add new prompt templates as needed for recurring tasks

### **Maintenance**

- Review and update prompts quarterly or after major project changes
- Keep prompts aligned with current project structure and priorities
- Add new prompts for recurring tasks that emerge during development

---

**Purpose**: Streamline project communication and reduce repetitive prompt creation  
**Maintenance**: Update prompts as project evolves and new patterns emerge  
**Usage**: Copy and customize prompts as needed for specific situations 