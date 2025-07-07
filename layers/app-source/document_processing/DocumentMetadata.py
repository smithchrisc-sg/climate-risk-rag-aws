"""
DocumentMetadata classes for Climate Risk RAG System
AWS-optimized metadata structures with confidence scoring
"""

import os
import sys
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict, field
import logging

@dataclass
class MetadataField:
    """Represents a metadata field with value and confidence score."""
    value: Any
    confidence: float
    source: str

    def __post_init__(self):
        """Validate confidence score range."""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence score must be between 0 and 1")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'value': self.value,
            'confidence': self.confidence,
            'source': self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataField':
        """Create from dictionary"""
        return cls(
            value=data.get('value'),
            confidence=data.get('confidence', 0.1),
            source=data.get('source', 'unknown')
        )

@dataclass
class StructuralMetadata:
    """Represents structural metadata of the document."""
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    paragraph_count: Optional[int] = None
    section_count: Optional[int] = None
    table_count: Optional[int] = None
    figure_count: Optional[int] = None
    has_toc: bool = False
    has_index: bool = False
    has_bibliography: bool = False
    document_type: Optional[str] = None
    layout_complexity: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StructuralMetadata':
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class DocumentDates:
    """Represents various dates associated with the document."""
    creation_date: Optional[MetadataField] = None
    modification_date: Optional[MetadataField] = None
    publication_date: Optional[MetadataField] = None
    download_date: Optional[datetime] = None
    processing_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {}
        for field_name, field_value in asdict(self).items():
            if field_value is not None:
                if isinstance(field_value, MetadataField):
                    result[field_name] = field_value.to_dict()
                elif isinstance(field_value, datetime):
                    result[field_name] = field_value.isoformat()
                else:
                    result[field_name] = field_value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentDates':
        """Create from dictionary"""
        result = {}
        for field_name, field_value in data.items():
            if field_name in cls.__dataclass_fields__:
                if field_name in ['download_date', 'processing_date'] and isinstance(field_value, str):
                    result[field_name] = datetime.fromisoformat(field_value)
                elif isinstance(field_value, dict) and 'value' in field_value:
                    result[field_name] = MetadataField.from_dict(field_value)
                else:
                    result[field_name] = field_value
        return cls(**result)

@dataclass
class DocumentMetadata:
    """
    Comprehensive document metadata with confidence scoring.
    AWS-optimized for PostgreSQL storage and Lambda processing.
    """
    
    # Basic identification
    doc_id: Optional[str] = None
    url: Optional[str] = None
    original_filename: Optional[str] = None
    
    # File paths (S3 or local)
    pdf_path: Optional[str] = None
    text_path: Optional[str] = None
    
    # Core metadata with confidence
    title: Optional[MetadataField] = None
    author: Optional[MetadataField] = None
    language: Optional[MetadataField] = None
    subject: Optional[MetadataField] = None
    keywords: Optional[MetadataField] = None
    
    # Dates
    dates: Optional[DocumentDates] = None
    
    # Structural information
    structural: Optional[StructuralMetadata] = None
    
    # Processing information
    processing_info: Dict[str, Any] = field(default_factory=dict)
    
    # Raw metadata from extraction
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Quality and source tracking
    metadata_quality: float = 0.1
    metadata_source: str = "initial"
    
    # Status tracking
    status: str = "pending"
    error_message: Optional[str] = None
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Initialize timestamps and validate data"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        
        # Initialize dates if not provided
        if self.dates is None:
            self.dates = DocumentDates()
        
        # Initialize structural metadata if not provided
        if self.structural is None:
            self.structural = StructuralMetadata()
        
        # Validate quality score
        if not 0 <= self.metadata_quality <= 1:
            raise ValueError("Metadata quality must be between 0 and 1")

    def update_field(self, field_name: str, value: Any, confidence: float, source: str):
        """Update a metadata field with confidence tracking"""
        if hasattr(self, field_name):
            setattr(self, field_name, MetadataField(value, confidence, source))
            self.updated_at = datetime.now()
            
            # Update overall quality based on confidence
            self._update_quality_score()
        else:
            raise ValueError(f"Unknown metadata field: {field_name}")

    def _update_quality_score(self):
        """Update overall metadata quality based on field confidences"""
        confidence_scores = []
        
        for field_name in ['title', 'author', 'language', 'subject']:
            field_value = getattr(self, field_name)
            if field_value and isinstance(field_value, MetadataField):
                confidence_scores.append(field_value.confidence)
        
        if confidence_scores:
            self.metadata_quality = sum(confidence_scores) / len(confidence_scores)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        result = {}
        
        # Basic fields
        for field_name in ['doc_id', 'url', 'original_filename', 'pdf_path', 'text_path', 
                          'status', 'error_message', 'metadata_quality', 'metadata_source']:
            value = getattr(self, field_name)
            if value is not None:
                result[field_name] = value
        
        # MetadataField objects
        for field_name in ['title', 'author', 'language', 'subject', 'keywords']:
            field_value = getattr(self, field_name)
            if field_value and isinstance(field_value, MetadataField):
                result[field_name] = field_value.to_dict()
        
        # Complex objects
        if self.dates:
            result['dates'] = self.dates.to_dict()
        
        if self.structural:
            result['structural'] = self.structural.to_dict()
        
        # JSON fields
        result['processing_info'] = self.processing_info
        result['raw_metadata'] = self.raw_metadata
        
        # Timestamps
        if self.created_at:
            result['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            result['updated_at'] = self.updated_at.isoformat()
        
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """Create DocumentMetadata from dictionary"""
        # Handle MetadataField objects
        metadata_fields = {}
        for field_name in ['title', 'author', 'language', 'subject', 'keywords']:
            if field_name in data and isinstance(data[field_name], dict):
                metadata_fields[field_name] = MetadataField.from_dict(data[field_name])
        
        # Handle dates
        dates = None
        if 'dates' in data:
            dates = DocumentDates.from_dict(data['dates'])
        
        # Handle structural metadata
        structural = None
        if 'structural' in data:
            structural = StructuralMetadata.from_dict(data['structural'])
        
        # Handle timestamps
        created_at = None
        updated_at = None
        if 'created_at' in data and isinstance(data['created_at'], str):
            created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            updated_at = datetime.fromisoformat(data['updated_at'])
        
        # Create instance
        return cls(
            doc_id=data.get('doc_id'),
            url=data.get('url'),
            original_filename=data.get('original_filename'),
            pdf_path=data.get('pdf_path'),
            text_path=data.get('text_path'),
            dates=dates,
            structural=structural,
            processing_info=data.get('processing_info', {}),
            raw_metadata=data.get('raw_metadata', {}),
            metadata_quality=data.get('metadata_quality', 0.1),
            metadata_source=data.get('metadata_source', 'initial'),
            status=data.get('status', 'pending'),
            error_message=data.get('error_message'),
            created_at=created_at,
            updated_at=updated_at,
            **metadata_fields
        )

    def merge_with(self, other: 'DocumentMetadata', prefer_higher_confidence: bool = True) -> 'DocumentMetadata':
        """
        Merge this metadata with another, optionally preferring higher confidence values.
        
        Args:
            other: Other DocumentMetadata to merge with
            prefer_higher_confidence: If True, prefer fields with higher confidence
            
        Returns:
            New DocumentMetadata with merged values
        """
        merged_data = self.to_dict()
        other_data = other.to_dict()
        
        # Merge MetadataField objects
        for field_name in ['title', 'author', 'language', 'subject', 'keywords']:
            self_field = getattr(self, field_name)
            other_field = getattr(other, field_name)
            
            if other_field and isinstance(other_field, MetadataField):
                if not self_field:
                    # Use other if self doesn't have this field
                    merged_data[field_name] = other_field.to_dict()
                elif prefer_higher_confidence and other_field.confidence > self_field.confidence:
                    # Use other if it has higher confidence
                    merged_data[field_name] = other_field.to_dict()
                # Otherwise keep self
        
        # Merge processing info
        merged_processing_info = self.processing_info.copy()
        merged_processing_info.update(other.processing_info)
        merged_data['processing_info'] = merged_processing_info
        
        # Merge raw metadata
        merged_raw_metadata = self.raw_metadata.copy()
        merged_raw_metadata.update(other.raw_metadata)
        merged_data['raw_metadata'] = merged_raw_metadata
        
        # Update timestamps
        merged_data['updated_at'] = datetime.now().isoformat()
        
        return DocumentMetadata.from_dict(merged_data)

    def validate(self) -> List[str]:
        """
        Validate metadata and return list of validation errors.
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check required fields
        if not self.doc_id:
            errors.append("doc_id is required")
        
        # Validate confidence scores
        for field_name in ['title', 'author', 'language', 'subject', 'keywords']:
            field_value = getattr(self, field_name)
            if field_value and isinstance(field_value, MetadataField):
                if not 0 <= field_value.confidence <= 1:
                    errors.append(f"{field_name} confidence must be between 0 and 1")
        
        # Validate quality score
        if not 0 <= self.metadata_quality <= 1:
            errors.append("metadata_quality must be between 0 and 1")
        
        # Validate status
        valid_statuses = ['pending', 'processing', 'completed', 'failed', 'error']
        if self.status not in valid_statuses:
            errors.append(f"status must be one of: {', '.join(valid_statuses)}")
        
        return errors

    def is_valid(self) -> bool:
        """Check if metadata is valid"""
        return len(self.validate()) == 0

    def __str__(self) -> str:
        """String representation"""
        title = self.title.value if self.title else "Unknown"
        author = self.author.value if self.author else "Unknown"
        return f"DocumentMetadata(id={self.doc_id}, title='{title}', author='{author}', quality={self.metadata_quality:.2f})"

    def __repr__(self) -> str:
        """Detailed representation"""
        return f"DocumentMetadata(doc_id='{self.doc_id}', status='{self.status}', quality={self.metadata_quality})"
