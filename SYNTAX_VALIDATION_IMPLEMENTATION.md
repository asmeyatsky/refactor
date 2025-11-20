# Syntax Validation Implementation

## Overview

The refactoring tool now **guarantees syntactically correct code output**. If the transformation produces invalid code, the system will:

1. **Attempt to fix** common syntax errors automatically
2. **Validate** the output before returning
3. **Fallback** to original code if fixes fail
4. **Retry** Gemini API calls if syntax validation fails

## Implementation Details

### 1. Gemini API Response Validation

**Location**: `infrastructure/adapters/__init__.py`

**Method**: `_extract_and_validate_response()`

- Validates `finish_reason` (handles truncated/blocked responses)
- Extracts code from markdown blocks
- **Validates Python syntax** using `ast.parse()` for code outputs
- Returns `None` if validation fails (triggers retry or fallback)

**Key Features**:
```python
if is_code:
    try:
        ast.parse(text)  # Validate syntax
        logger.debug("Generated code passed syntax validation")
    except SyntaxError as e:
        logger.error(f"Generated code has syntax error: {e}")
        return None  # Triggers retry
```

### 2. Retry Logic with Enhanced Prompts

**Location**: `infrastructure/adapters/__init__.py`

**Method**: `_generate_recipe_with_gemini()`

- **3 retry attempts** if syntax validation fails
- **Lower temperature** on retries (0.2 → 0.1) for more deterministic output
- **Enhanced prompts** on retry with explicit syntax requirements
- Falls back to mock recipe if all retries fail

**Retry Flow**:
```
Attempt 1: temperature=0.2 → Validate → If fails:
Attempt 2: temperature=0.1 + enhanced prompt → Validate → If fails:
Attempt 3: temperature=0.1 + enhanced prompt → Validate → If fails:
Fallback: Use mock recipe
```

### 3. Transformation Output Validation

**Location**: `infrastructure/adapters/extended_semantic_engine.py`

**Method**: `_validate_and_fix_syntax()`

- **Validates** transformed code syntax before returning
- **Attempts to fix** common issues:
  - Double assignments (`response = bucket = ...`)
  - Incorrect indentation
  - Malformed statements
- **Falls back** to original code if fixes fail
- **Never returns invalid code**

**Fix Attempts**:
1. Parse code with `ast.parse()`
2. If syntax error, attempt automatic fixes:
   - Fix double assignments
   - Fix indentation issues
   - Remove incorrectly indented standalone statements
3. Re-validate fixed code
4. If still invalid, return original code (ensures valid output)

### 4. Enhanced Prompts

**Location**: `infrastructure/adapters/__init__.py`

**Method**: `_generate_recipe_with_gemini()`

Prompts now include explicit syntax requirements:
```
CRITICAL REQUIREMENTS:
1. Generate ONLY syntactically correct Python code
2. Use proper indentation (exactly 4 spaces per level, no tabs)
3. All code must be executable and valid Python syntax
...
```

## Error Handling Flow

```
User Code → Gemini API → Response Extraction → Syntax Validation
                                                      ↓
                                              Valid? → Yes → Return Code
                                                      ↓
                                              No → Attempt Fix → Validate
                                                      ↓
                                              Still Invalid? → Return Original Code
```

## Benefits

1. **Guaranteed Valid Output**: System never returns syntactically invalid code
2. **Automatic Fixes**: Common issues are fixed automatically
3. **Graceful Degradation**: Falls back to original code if transformation fails
4. **Better LLM Output**: Retry logic with enhanced prompts improves quality
5. **Comprehensive Logging**: All validation failures are logged for debugging

## Testing

To verify syntax validation works:

```python
# Test with invalid code (like gcttool.py output)
bad_code = """bucket = s3_client.bucket("my-bucket")
    blob = bucket.blob("remote_file.txt")  # Wrong indentation
    blob.upload_from_filename("local_file.txt")
"""

# This will be caught and fixed/returned as original
transformed = engine.transform_code(bad_code, 'python', recipe)
# Result: Either fixed code or original code (never invalid code)
```

## Configuration

No additional configuration needed. Syntax validation is enabled by default for:
- Python code transformations
- Gemini API recipe generation
- All code output from transformations

## Future Enhancements

Potential improvements:
1. More sophisticated syntax fixing (using lib2to3 or autopep8)
2. Code formatting (black/autopep8) after transformation
3. Linting validation (pylint/flake8) in addition to syntax
4. Language-specific validators for Java, etc.
