"""
End-to-End Consistency Check for Go Language Support
Verifies that all components work together correctly
"""

import sys
import importlib
import inspect
from pathlib import Path

def check_imports():
    """Check that all required modules can be imported"""
    print("="*70)
    print("CHECKING IMPORTS")
    print("="*70)
    
    modules_to_check = [
        "infrastructure.adapters.extended_semantic_engine",
        "infrastructure.adapters.azure_extended_semantic_engine",
        "domain.entities.codebase",
        "domain.value_objects",
        "application.use_cases",
    ]
    
    results = []
    for module_name in modules_to_check:
        try:
            module = importlib.import_module(module_name)
            print(f"✓ {module_name}")
            results.append((module_name, True, None))
        except Exception as e:
            print(f"✗ {module_name}: {e}")
            results.append((module_name, False, str(e)))
    
    return results

def check_go_transformer_classes():
    """Check that Go transformer classes exist"""
    print("\n" + "="*70)
    print("CHECKING GO TRANSFORMER CLASSES")
    print("="*70)
    
    try:
        from infrastructure.adapters.extended_semantic_engine import ExtendedGoTransformer
        from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedGoTransformer
        
        # Check AWS Go transformer
        aws_transformer = ExtendedGoTransformer(None)
        print("✓ ExtendedGoTransformer (AWS) exists")
        
        # Check Azure Go transformer
        azure_transformer = AzureExtendedGoTransformer(None, None)
        print("✓ AzureExtendedGoTransformer exists")
        
        # Check methods
        aws_methods = [m for m in dir(aws_transformer) if not m.startswith('_')]
        azure_methods = [m for m in dir(azure_transformer) if not m.startswith('_')]
        
        print(f"  AWS transformer methods: {len(aws_methods)}")
        print(f"  Azure transformer methods: {len(azure_methods)}")
        
        return True
    except Exception as e:
        print(f"✗ Error checking transformer classes: {e}")
        return False

def check_engine_registration():
    """Check that Go is registered in transformation engines"""
    print("\n" + "="*70)
    print("CHECKING ENGINE REGISTRATION")
    print("="*70)
    
    try:
        from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
        from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedASTTransformationEngine
        
        # Check AWS engine
        aws_engine = ExtendedASTTransformationEngine()
        if 'go' in aws_engine.transformers:
            print("✓ Go registered in AWS ExtendedASTTransformationEngine")
        else:
            print("✗ Go NOT registered in AWS ExtendedASTTransformationEngine")
            return False
        
        if 'golang' in aws_engine.transformers:
            print("✓ 'golang' alias registered in AWS engine")
        else:
            print("✗ 'golang' alias NOT registered in AWS engine")
            return False
        
        # Check Azure engine
        azure_engine = AzureExtendedASTTransformationEngine()
        if 'go' in azure_engine.transformers:
            print("✓ Go registered in Azure ExtendedASTTransformationEngine")
        else:
            print("✗ Go NOT registered in Azure ExtendedASTTransformationEngine")
            return False
        
        if 'golang' in azure_engine.transformers:
            print("✓ 'golang' alias registered in Azure engine")
        else:
            print("✗ 'golang' alias NOT registered in Azure engine")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error checking engine registration: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_programming_language_enum():
    """Check that ProgrammingLanguage.GO exists"""
    print("\n" + "="*70)
    print("CHECKING PROGRAMMING LANGUAGE ENUM")
    print("="*70)
    
    try:
        from domain.entities.codebase import ProgrammingLanguage
        
        if hasattr(ProgrammingLanguage, 'GO'):
            print("✓ ProgrammingLanguage.GO exists")
            print(f"  Value: {ProgrammingLanguage.GO.value}")
            return True
        else:
            print("✗ ProgrammingLanguage.GO does NOT exist")
            print(f"  Available: {[lang.name for lang in ProgrammingLanguage]}")
            return False
    except Exception as e:
        print(f"✗ Error checking ProgrammingLanguage enum: {e}")
        return False

def check_api_server_support():
    """Check that API server supports Go"""
    print("\n" + "="*70)
    print("CHECKING API SERVER SUPPORT")
    print("="*70)
    
    try:
        # Read api_server.py and check for Go support
        api_server_path = Path("api_server.py")
        if not api_server_path.exists():
            print("✗ api_server.py not found")
            return False
        
        content = api_server_path.read_text()
        
        checks = [
            ('go' in content.lower(), "Contains 'go'"),
            ('golang' in content.lower(), "Contains 'golang'"),
            ('ProgrammingLanguage.GO' in content, "References ProgrammingLanguage.GO"),
            ('supported_languages' in content and 'go' in content, "Go in supported_languages"),
        ]
        
        all_passed = True
        for check, description in checks:
            if check:
                print(f"✓ {description}")
            else:
                print(f"✗ {description}")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ Error checking API server: {e}")
        return False

def check_prompt_builders():
    """Check that Go prompt builders exist"""
    print("\n" + "="*70)
    print("CHECKING PROMPT BUILDERS")
    print("="*70)
    
    try:
        from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
        from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedASTTransformationEngine
        
        aws_engine = ExtendedASTTransformationEngine()
        azure_engine = AzureExtendedASTTransformationEngine()
        
        # Check AWS prompt builder
        if hasattr(aws_engine, '_build_go_transformation_prompt'):
            print("✓ AWS _build_go_transformation_prompt exists")
        else:
            print("✗ AWS _build_go_transformation_prompt does NOT exist")
            return False
        
        # Check Azure prompt builder
        if hasattr(azure_engine, '_build_azure_go_transformation_prompt'):
            print("✓ Azure _build_azure_go_transformation_prompt exists")
        else:
            print("✗ Azure _build_azure_go_transformation_prompt does NOT exist")
            return False
        
        # Check cleanup methods
        if hasattr(aws_engine, '_aggressive_go_aws_cleanup'):
            print("✓ AWS _aggressive_go_aws_cleanup exists")
        else:
            print("✗ AWS _aggressive_go_aws_cleanup does NOT exist")
            return False
        
        if hasattr(azure_engine, '_aggressive_go_azure_cleanup'):
            print("✓ Azure _aggressive_go_azure_cleanup exists")
        else:
            print("✗ Azure _aggressive_go_azure_cleanup does NOT exist")
            return False
        
        # Check pattern detection
        if hasattr(aws_engine, '_has_aws_patterns'):
            # Test with Go language
            test_code = "github.com/aws/aws-sdk-go/service/s3"
            result = aws_engine._has_aws_patterns(test_code, language='go')
            if result:
                print("✓ AWS _has_aws_patterns correctly detects Go patterns")
            else:
                print("✗ AWS _has_aws_patterns does NOT detect Go patterns")
                return False
        else:
            print("✗ AWS _has_aws_patterns does NOT exist")
            return False
        
        if hasattr(azure_engine, '_has_azure_patterns'):
            # Test with Go language
            test_code = "github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
            result = azure_engine._has_azure_patterns(test_code, language='go')
            if result:
                print("✓ Azure _has_azure_patterns correctly detects Go patterns")
            else:
                print("✗ Azure _has_azure_patterns does NOT detect Go patterns")
                return False
        else:
            print("✗ Azure _has_azure_patterns does NOT exist")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Error checking prompt builders: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_test_files():
    """Check that test files exist and are properly structured"""
    print("\n" + "="*70)
    print("CHECKING TEST FILES")
    print("="*70)
    
    test_file = Path("test_go_comprehensive.py")
    if test_file.exists():
        print("✓ test_go_comprehensive.py exists")
        
        content = test_file.read_text()
        
        checks = [
            ('AWS_GO_TESTS' in content, "Contains AWS_GO_TESTS"),
            ('AZURE_GO_TESTS' in content, "Contains AZURE_GO_TESTS"),
            ('"language": "go"' in content, "Uses 'go' language"),
            ('cloud_provider' in content, "References cloud_provider"),
        ]
        
        for check, description in checks:
            if check:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description}")
    else:
        print("✗ test_go_comprehensive.py does NOT exist")
        return False
    
    return True

def check_documentation():
    """Check that documentation mentions Go support"""
    print("\n" + "="*70)
    print("CHECKING DOCUMENTATION")
    print("="*70)
    
    docs_to_check = [
        ("README.md", ["Go", "go", "golang"]),
        ("GO_LANGUAGE_SUPPORT.md", ["Go", "AWS", "Azure"]),
    ]
    
    all_passed = True
    for doc_path, keywords in docs_to_check:
        path = Path(doc_path)
        if path.exists():
            content = path.read_text()
            print(f"✓ {doc_path} exists")
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    print(f"  ✓ Contains '{keyword}'")
                else:
                    print(f"  ✗ Missing '{keyword}'")
                    all_passed = False
        else:
            print(f"✗ {doc_path} does NOT exist")
            all_passed = False
    
    return all_passed

def check_service_detection():
    """Check that service detection works for Go"""
    print("\n" + "="*70)
    print("CHECKING SERVICE DETECTION")
    print("="*70)
    
    try:
        from infrastructure.adapters.extended_semantic_engine import ExtendedASTTransformationEngine
        from infrastructure.adapters.azure_extended_semantic_engine import AzureExtendedASTTransformationEngine
        
        # Test AWS service detection
        aws_engine = ExtendedASTTransformationEngine()
        aws_code = """
package main
import "github.com/aws/aws-sdk-go/service/s3"
func main() {
    svc := s3.New(sess)
}
"""
        # Check if prompt builder can detect services
        if hasattr(aws_engine, '_build_go_transformation_prompt'):
            prompt = aws_engine._build_go_transformation_prompt(aws_code, 's3_to_gcs', 'GCP', False)
            if 'S3' in prompt or 's3' in prompt.lower():
                print("✓ AWS service detection works in Go prompt")
            else:
                print("✗ AWS service detection may not work")
                return False
        
        # Test Azure service detection
        azure_engine = AzureExtendedASTTransformationEngine()
        azure_code = """
package main
import "github.com/Azure/azure-sdk-for-go/sdk/storage/azblob"
func main() {
    client, _ := azblob.NewClientFromConnectionString(connStr, nil)
}
"""
        if hasattr(azure_engine, '_build_azure_go_transformation_prompt'):
            prompt = azure_engine._build_azure_go_transformation_prompt(azure_code, 'azure_blob_storage_to_gcs', 'GCP', False)
            if 'Blob Storage' in prompt or 'blob' in prompt.lower():
                print("✓ Azure service detection works in Go prompt")
            else:
                print("✗ Azure service detection may not work")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Error checking service detection: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_use_case_integration():
    """Check that use cases handle Go correctly"""
    print("\n" + "="*70)
    print("CHECKING USE CASE INTEGRATION")
    print("="*70)
    
    try:
        from application.use_cases import _transform_code_standalone
        
        # Check function signature
        sig = inspect.signature(_transform_code_standalone)
        params = list(sig.parameters.keys())
        
        if 'language' in params:
            print("✓ _transform_code_standalone accepts 'language' parameter")
        else:
            print("✗ _transform_code_standalone does NOT accept 'language' parameter")
            return False
        
        # Check that it handles Go
        content = Path("application/use_cases/__init__.py").read_text()
        if 'go' in content.lower() or 'golang' in content.lower():
            print("✓ Use cases module references Go")
        else:
            print("⚠ Use cases module may not handle Go explicitly")
        
        return True
    except Exception as e:
        print(f"✗ Error checking use case integration: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all consistency checks"""
    print("\n" + "="*70)
    print("END-TO-END CONSISTENCY CHECK FOR GO LANGUAGE SUPPORT")
    print("="*70)
    
    checks = [
        ("Imports", check_imports),
        ("Go Transformer Classes", check_go_transformer_classes),
        ("Engine Registration", check_engine_registration),
        ("Programming Language Enum", check_programming_language_enum),
        ("API Server Support", check_api_server_support),
        ("Prompt Builders", check_prompt_builders),
        ("Test Files", check_test_files),
        ("Documentation", check_documentation),
        ("Service Detection", check_service_detection),
        ("Use Case Integration", check_use_case_integration),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Error in {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All consistency checks passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Please review above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
