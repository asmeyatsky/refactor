"""
Toon Format Serializer

Architectural Intent:
- Implements Token-Oriented Object Notation (TOON) format for token optimization
- Converts JSON data structures to compact TOON format for LLM prompts
- Reduces token usage by 50-80% compared to JSON
"""

from typing import Any, Dict, List, Union
import json


class ToonSerializer:
    """
    Serializes Python data structures to TOON format for token optimization.
    
    TOON combines YAML's indentation with CSV-style tabular layout for arrays.
    It's optimized for uniform arrays of objects (the common case in our data).
    """
    
    @staticmethod
    def to_toon(data: Any, indent: int = 0) -> str:
        """
        Convert Python data structure to TOON format.
        
        Args:
            data: Python dict, list, or primitive value
            indent: Current indentation level
            
        Returns:
            TOON-formatted string
        """
        if data is None:
            return "null"
        elif isinstance(data, bool):
            return "true" if data else "false"
        elif isinstance(data, (int, float)):
            return str(data)
        elif isinstance(data, str):
            # Escape strings if needed
            if any(c in data for c in ['\n', '\t', ':', '|', '#']):
                return json.dumps(data)  # Use JSON string format for complex strings
            return data
        elif isinstance(data, list):
            return ToonSerializer._list_to_toon(data, indent)
        elif isinstance(data, dict):
            return ToonSerializer._dict_to_toon(data, indent)
        else:
            return str(data)
    
    @staticmethod
    def _list_to_toon(data: List[Any], indent: int) -> str:
        """Convert list to TOON format"""
        if not data:
            return "[]"
        
        # Check if it's a uniform array of objects (TOON's sweet spot)
        if all(isinstance(item, dict) for item in data) and len(data) > 0:
            # Check if all objects have the same keys (uniform)
            first_keys = set(data[0].keys())
            if all(set(item.keys()) == first_keys for item in data):
                return ToonSerializer._uniform_array_to_toon(data, indent)
        
        # Non-uniform or primitive array - use YAML-style
        lines = []
        for item in data:
            item_str = ToonSerializer.to_toon(item, indent + 1)
            if isinstance(item, (dict, list)):
                lines.append(f"{'  ' * indent}- {item_str.split(chr(10))[0]}")
                # Add remaining lines with proper indentation
                remaining = item_str.split(chr(10))[1:]
                for line in remaining:
                    if line.strip():
                        lines.append(f"{'  ' * (indent + 1)}{line}")
            else:
                lines.append(f"{'  ' * indent}- {item_str}")
        return '\n'.join(lines)
    
    @staticmethod
    def _uniform_array_to_toon(data: List[Dict], indent: int) -> str:
        """
        Convert uniform array of objects to TOON tabular format.
        This is TOON's strength - CSV-like compactness for arrays.
        """
        if not data:
            return "[]"
        
        lines = []
        keys = list(data[0].keys())
        
        # Header row (CSV-style)
        header = ' | '.join(str(k) for k in keys)
        lines.append(f"{'  ' * indent}{header}")
        
        # Separator
        separator = '-+-'.join(['-' * len(str(k)) for k in keys])
        lines.append(f"{'  ' * indent}{separator}")
        
        # Data rows
        for item in data:
            row_values = []
            for key in keys:
                value = item.get(key, '')
                # Convert value to string, handling special cases
                if isinstance(value, (dict, list)):
                    # For nested structures, use compact representation
                    value_str = json.dumps(value) if isinstance(value, dict) else str(value)
                elif value is None:
                    value_str = ''
                elif isinstance(value, bool):
                    value_str = 'true' if value else 'false'
                else:
                    value_str = str(value)
                
                # Truncate long values
                if len(value_str) > 50:
                    value_str = value_str[:47] + '...'
                
                row_values.append(value_str)
            
            row = ' | '.join(row_values)
            lines.append(f"{'  ' * indent}{row}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def _dict_to_toon(data: Dict[str, Any], indent: int) -> str:
        """Convert dict to TOON format (YAML-style)"""
        if not data:
            return "{}"
        
        lines = []
        for key, value in data.items():
            key_str = str(key)
            value_str = ToonSerializer.to_toon(value, indent + 1)
            
            if isinstance(value, (dict, list)):
                # Multi-line value
                lines.append(f"{'  ' * indent}{key_str}:")
                # Add value lines with proper indentation
                value_lines = value_str.split('\n')
                for line in value_lines:
                    if line.strip():
                        lines.append(line if line.startswith('  ') else f"{'  ' * (indent + 1)}{line}")
            else:
                # Single-line value
                lines.append(f"{'  ' * indent}{key_str}: {value_str}")
        
        return '\n'.join(lines)
    
    @staticmethod
    def from_toon(toon_str: str) -> Any:
        """
        Parse TOON format back to Python data structure.
        This is a simplified parser - full implementation would handle all edge cases.
        """
        # For now, use a simple approach - convert TOON-like structures
        # In production, implement full TOON parser
        try:
            # Try to parse as JSON first (fallback)
            return json.loads(toon_str)
        except:
            # Simple TOON parser for common cases
            return ToonSerializer._parse_toon_simple(toon_str)
    
    @staticmethod
    def _parse_toon_simple(toon_str: str) -> Any:
        """Simple TOON parser for basic structures"""
        lines = [line.rstrip() for line in toon_str.strip().split('\n') if line.strip()]
        
        if not lines:
            return {}
        
        # Check if it's a tabular array (has | separator)
        if ' | ' in lines[0] and len(lines) > 1 and '-' in lines[1]:
            return ToonSerializer._parse_tabular_array(lines)
        
        # Otherwise parse as YAML-like structure
        return ToonSerializer._parse_yaml_like(lines)
    
    @staticmethod
    def _parse_tabular_array(lines: List[str]) -> List[Dict]:
        """Parse TOON tabular array format"""
        if len(lines) < 2:
            return []
        
        # Parse header
        header = [col.strip() for col in lines[0].split('|')]
        
        # Skip separator line
        data_lines = lines[2:] if '-' in lines[1] else lines[1:]
        
        result = []
        for line in data_lines:
            if not line.strip():
                continue
            values = [col.strip() for col in line.split('|')]
            item = {}
            for i, key in enumerate(header):
                if i < len(values):
                    value = values[i]
                    # Try to parse value
                    if value == '':
                        item[key] = None
                    elif value.lower() == 'true':
                        item[key] = True
                    elif value.lower() == 'false':
                        item[key] = False
                    else:
                        try:
                            # Try number
                            if '.' in value:
                                item[key] = float(value)
                            else:
                                item[key] = int(value)
                        except:
                            item[key] = value
            result.append(item)
        
        return result
    
    @staticmethod
    def _parse_yaml_like(lines: List[str]) -> Dict:
        """Parse YAML-like TOON structure"""
        result = {}
        stack = [(0, result)]  # (indent_level, current_dict)
        
        for line in lines:
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # Calculate indent
            indent = len(line) - len(line.lstrip())
            stripped = line.strip()
            
            if ':' in stripped:
                key, value = stripped.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Find the right parent based on indent
                while stack and stack[-1][0] >= indent:
                    stack.pop()
                
                parent = stack[-1][1] if stack else result
                
                if value:
                    # Simple value
                    parent[key] = ToonSerializer._parse_value(value)
                else:
                    # Nested structure
                    new_dict = {}
                    parent[key] = new_dict
                    stack.append((indent, new_dict))
        
        return result
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """Parse a single value"""
        value = value.strip()
        if value == 'null':
            return None
        elif value == 'true':
            return True
        elif value == 'false':
            return False
        elif value.startswith('"') and value.endswith('"'):
            return json.loads(value)
        else:
            try:
                if '.' in value:
                    return float(value)
                return int(value)
            except:
                return value


def to_toon(data: Any) -> str:
    """Convenience function to convert data to TOON format"""
    return ToonSerializer.to_toon(data)


def from_toon(toon_str: str) -> Any:
    """Convenience function to parse TOON format"""
    return ToonSerializer.from_toon(toon_str)
