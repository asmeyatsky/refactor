"""
Memory Module for Context Management

Architectural Intent:
- Store long-term context (code structure, dependency map)
- Store short-term context (current task status, previous failures/lessons learned)
- Implement the Memory Module component as described in the PRD
- Use appropriate storage (vector database for long-term, cache for short-term)
"""

import json
import pickle
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, asdict
import os


@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    key: str
    value: Any
    timestamp: datetime
    metadata: Dict[str, Any]
    tags: List[str]


class MemoryModule:
    """
    Memory Module - Context Management Component
    
    Stores:
    - Long-term context: code structure, dependency map
    - Short-term context: current task status, previous failures/lessons learned
    """
    
    def __init__(self, storage_path: str = "/tmp/memory_module"):
        self.storage_path = storage_path
        self.long_term_storage: Dict[str, MemoryEntry] = {}
        self.short_term_cache: Dict[str, MemoryEntry] = {}
        
        # Create storage directory
        os.makedirs(storage_path, exist_ok=True)
        
        # Load any existing long-term memories
        self._load_long_term_memories()
    
    def store_long_term(self, key: str, value: Any, metadata: Dict[str, Any] = None, tags: List[str] = None) -> None:
        """Store information in long-term memory"""
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            metadata=metadata or {},
            tags=tags or []
        )
        
        self.long_term_storage[key] = entry
        self._save_long_term_memories()
    
    def store_short_term(self, key: str, value: Any, metadata: Dict[str, Any] = None, tags: List[str] = None) -> None:
        """Store information in short-term cache"""
        entry = MemoryEntry(
            key=key,
            value=value,
            timestamp=datetime.now(),
            metadata=metadata or {},
            tags=tags or []
        )
        
        self.short_term_cache[key] = entry
    
    def retrieve_long_term(self, key: str) -> Optional[Any]:
        """Retrieve information from long-term memory"""
        entry = self.long_term_storage.get(key)
        return entry.value if entry else None
    
    def retrieve_short_term(self, key: str) -> Optional[Any]:
        """Retrieve information from short-term cache"""
        entry = self.short_term_cache.get(key)
        return entry.value if entry else None
    
    def search_by_tags(self, tags: List[str], memory_type: str = "both") -> List[MemoryEntry]:
        """Search memories by tags"""
        results = []
        
        if memory_type in ["long", "both"]:
            for entry in self.long_term_storage.values():
                if any(tag in entry.tags for tag in tags):
                    results.append(entry)
        
        if memory_type in ["short", "both"]:
            for entry in self.short_term_cache.values():
                if any(tag in entry.tags for tag in tags):
                    results.append(entry)
        
        return results
    
    def get_lessons_learned(self, task_id: str) -> List[Dict[str, Any]]:
        """Get lessons learned for a specific task"""
        lessons = self.search_by_tags([f"lesson_{task_id}"], "long")
        return [lesson.value for lesson in lessons]
    
    def store_lesson(self, task_id: str, lesson: Dict[str, Any]) -> None:
        """Store a lesson learned from a task"""
        key = f"lesson_{task_id}_{datetime.now().isoformat()}"
        self.store_long_term(key, lesson, tags=[f"lesson_{task_id}", "lesson"])
    
    def _save_long_term_memories(self) -> None:
        """Persist long-term memories to storage"""
        file_path = os.path.join(self.storage_path, "long_term_memories.pkl")
        with open(file_path, 'wb') as f:
            pickle.dump(self.long_term_storage, f)
    
    def _load_long_term_memories(self) -> None:
        """Load long-term memories from storage"""
        file_path = os.path.join(self.storage_path, "long_term_memories.pkl")
        if os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                self.long_term_storage = pickle.load(f)


class ContextManager:
    """
    Context Manager for the Refactoring Agent
    
    Manages the focused working context required by LLMs as mentioned in the PRD.
    Ensures that only relevant file, requirement, and goal are provided for each
    atomic refactoring step.
    """
    
    def __init__(self, memory_module: MemoryModule):
        self.memory_module = memory_module
        self.current_context: Dict[str, Any] = {}
    
    def set_current_task_context(self, task_id: str, context_data: Dict[str, Any]) -> None:
        """Set the context for the current task"""
        self.current_context = {
            "task_id": task_id,
            "data": context_data,
            "timestamp": datetime.now()
        }
        
        # Store in short-term memory
        self.memory_module.store_short_term(
            f"current_task_context_{task_id}",
            context_data,
            tags=["current_context", task_id]
        )
    
    def get_current_task_context(self) -> Dict[str, Any]:
        """Get the context for the current task"""
        return self.current_context
    
    def build_focused_context(self, file_path: str, requirement: str, goal: str) -> Dict[str, Any]:
        """Build a focused working context for an atomic refactoring step"""
        # Retrieve relevant information from memory
        code_structure = self.memory_module.retrieve_long_term(f"code_structure_{file_path}")
        dependency_map = self.memory_module.retrieve_long_term(f"dependencies_{file_path}")
        
        # Get lessons learned for similar tasks
        lessons = self.memory_module.get_lessons_learned("s3_to_gcs_migration")
        
        focused_context = {
            "file_path": file_path,
            "requirement": requirement,
            "goal": goal,
            "code_structure": code_structure,
            "dependencies": dependency_map,
            "lessons_learned": lessons,
            "timestamp": datetime.now().isoformat()
        }
        
        return focused_context
    
    def update_context_with_task_result(self, task_id: str, result: Dict[str, Any]) -> None:
        """Update context with the result of a completed task"""
        # Store the result in memory as a lesson learned
        if not result.get('success'):
            self.memory_module.store_lesson(
                task_id,
                {
                    "result": result,
                    "error": result.get('error'),
                    "timestamp": datetime.now().isoformat(),
                    "task_id": task_id
                }
            )
        
        # Update current context if it was for this task
        if self.current_context.get("task_id") == task_id:
            self.current_context["result"] = result
            self.current_context["completed_at"] = datetime.now()
    
    def clear_task_context(self, task_id: str) -> None:
        """Clear context for a completed task"""
        if self.current_context.get("task_id") == task_id:
            self.current_context = {}


class AgentCollaborationContext:
    """
    Context management for multi-agent collaboration
    
    Manages the shared context between Planner, Refactoring Engine, and Verification agents
    as described in the PRD's multi-agent framework.
    """
    
    def __init__(self, memory_module: MemoryModule):
        self.memory_module = memory_module
    
    def share_analysis_result(self, analysis_result: Dict[str, Any], agents: List[str]) -> None:
        """Share analysis results between agents"""
        key = f"analysis_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory_module.store_long_term(
            key, 
            analysis_result, 
            metadata={"shared_with": agents},
            tags=["analysis", "shared"]
        )
    
    def share_lesson_learned(self, lesson: Dict[str, Any], from_agent: str, to_agents: List[str]) -> None:
        """Share lessons learned between agents (De-Hallucinator pattern)"""
        key = f"lesson_{from_agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.memory_module.store_long_term(
            key,
            lesson,
            metadata={"from_agent": from_agent, "to_agents": to_agents},
            tags=["lesson", "collaboration"]
        )
    
    def get_shared_context(self, context_type: str) -> List[Dict[str, Any]]:
        """Get shared context of a specific type"""
        entries = self.memory_module.search_by_tags([context_type], "long")
        return [entry.value for entry in entries]