"""
Dataset Manager
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

class DatasetManager:
    def __init__(self):
        self.datasets = {
            "cve": {},
            "multiple_host": {},
            "full_chain": {},
            "defense": {}
        }
        self._load_datasets()
    
    def _load_datasets(self):
        """Load all datasets from the JSON file"""
        json_path = Path(__file__).parent / "datasets.json"
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                self.datasets = json.load(f)
        else:
            print(f"⚠️ Not found {json_path}, please run convert_excel_to_json.py to generate datasets")
    
    def get_datasets(self, category: Optional[str] = None) -> Dict:
        """Get datasets"""
        if category:
            return self.datasets.get(category, {})
        return self.datasets
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task by ID or name"""
        for category, tasks in self.datasets.items():
            for task_name, info in tasks.items():
                if str(info['id']) == str(task_id) or task_name == task_id:
                    return info
        return None
    
    def list_categories(self) -> List[str]:
        """List all dataset categories"""
        return list(self.datasets.keys())
    
    def list_tasks(self, category: Optional[str] = None) -> List[str]:
        """List tasks"""
        if category:
            return list(self.datasets.get(category, {}).keys())
        
        all_tasks = []
        for tasks in self.datasets.values():
            all_tasks.extend(tasks.keys())
        return all_tasks

# Global instance
dataset_manager = DatasetManager() 