from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ResponseModel:
    """Simple response model for API endpoints"""
    success: bool
    message: str
    data: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary for JSON serialization"""
        result = {
            "success": self.success,
            "message": self.message
        }
        if self.data:
            result["data"] = self.data
        return result
