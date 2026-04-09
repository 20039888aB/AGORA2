"""
Run All Validations - Complete System Proof

This module runs all validation tests to prove the system
actually works under real-world conditions.
"""

import os
import sys
import time
import traceback
from datetime import datetime
import unittest
from io import StringIO

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import all validation modules
from .real_system_tests import run_real_system_tests
from .security_validation import run_security_validation
from .performance_validation import run_performance_validation
from .service_integrity_validation import run_service_integrity_validation


class ValidationRunner:
    """Comprehensive validation runner"""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
    
    def run_validation(self, name, validation_func):
        """Run a single validation"""
        print(f"\n{'='*80}")
        print(f"🧪 RUNNING {name.upper()}")
        print(f"{'='*80}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Capture output
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()
            
            # Run validation
            start_time = time.time()
            success = validation_func()
            duration = time.time() - start_time
            
            # Restore stdout
            sys.stdout = old_stdout
            output = captured_output.getvalue()
            
            # Store results
            self.results[name] = {
                'success': success,
                'duration': duration,
                'output': output,
                'error': None
            }
            
            print(f"\n{'='*80}")
            print(f"✅ {name.upper()}: {'PASSED' if success else 'FAILED'}")
            print(f"Duration: {duration:.2f}s")
            print(f"{'='*80}")
            
            return success
            
        except Exception as e:
            # Restore stdout
            sys.stdout = old_stdout
            
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            
            self.results[name] = {
                'success': False,
                'duration': 0,
                'output': '',
                'error': error_msg
            }
            
            print(f"\n{'='*80}")
            print(f"❌ {name.upper()}: FAILED WITH ERROR")
            print(f"Error: {error_msg}")
            print(f"{'='*80}")
            
            return False
    
    def run_all_validations(self):
        """Run all validations"""
        print(f"\n🚀 AGORAPROF LMS - COMPREHENSIVE SYSTEM VALIDATION")
        print(f"{'='*80}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        # Define all validations
        validations = [
            ("Real System Tests", run_real_system_tests),
            ("Security Validation", run_security_validation),
            ("Performance Validation", run_performance_validation),
            ("Service Integrity Validation", run_service_integrity_validation),
        ]
        
        # Run all validations
        passed_count = 0
        total_count = len(validations)
        
        for name, validation_func in validations:
            success = self.run_validation(name, validation_func)
            if success:
                passed_count += 1
            
            # Small delay between validations
            time.sleep(1)
        
        # Generate final report
        self.generate_final_report(passed_count, total_count)
        
        return passed_count == total_count
    
    def generate_final_report(self, passed_count, total_count):
        """Generate final validation report"""
        total_duration = time.time() - self.start_time
        
        print(f"\n{'='*80}")
        print(f"📊 FINAL VALIDATION REPORT")
        print(f"{'='*80}")
        print(f"Total Duration: {total_duration:.2f}s")
        print(f"Validations Passed: {passed_count}/{total_count}")
        print(f"Success Rate: {(passed_count/total_count)*100:.1f}%")
        print(f"{'='*80}")
        
        # Detailed results
        for name, result in self.results.items():
            status = "✅ PASSED" if result['success'] else "❌ FAILED"
            duration = result['duration']
            
            print(f"\n{name}:")
            print(f"  Status: {status}")
            print(f"  Duration: {duration:.2f}s")
            
            if result['error']:
                print(f"  Error: {result['error'][:200]}...")
        
        # Overall status
        overall_success = passed_count == total_count
        overall_status = "🎉 ALL VALIDATIONS PASSED" if overall_success else "❌ SOME VALIDATIONS FAILED"
        
        print(f"\n{'='*80}")
        print(f"🏆 OVERALL STATUS: {overall_status}")
        print(f"{'='*80}")
        
        # Recommendations
        if overall_success:
            print(f"\n🚀 SYSTEM IS PRODUCTION READY!")
            print(f"✅ Multi-tenancy security validated")
            print(f"✅ Performance under load verified")
            print(f"✅ Service layer integrity confirmed")
            print(f"✅ Real-world concurrency tested")
            print(f"\n🎯 READY FOR:")
            print(f"  • Production deployment")
            print(f"  • Frontend development")
            print(f"  • Enterprise scaling")
        else:
            print(f"\n⚠️  SYSTEM NEEDS ATTENTION!")
            failed_validations = [name for name, result in self.results.items() if not result['success']]
            
            print(f"❌ Failed validations:")
            for name in failed_validations:
                print(f"  • {name}")
            
            print(f"\n🔧 RECOMMENDED ACTIONS:")
            print(f"  • Fix failed validations")
            print(f"  • Re-run validation suite")
            print(f"  • Address performance issues")
            print(f"  • Strengthen security measures")
        
        print(f"\n{'='*80}")
        print(f"Validation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
        return overall_success


class ValidationReportGenerator:
    """Generate detailed validation reports"""
    
    def __init__(self, results):
        self.results = results
    
    def generate_html_report(self, filename='validation_report.html'):
        """Generate HTML validation report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AgoraProf LMS - Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .validation {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .passed {{ background-color: #d4edda; border-color: #c3e6cb; }}
        .failed {{ background-color: #f8d7da; border-color: #f5c6cb; }}
        .summary {{ background-color: #e2e3e5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .status {{ font-weight: bold; font-size: 18px; }}
        .details {{ margin-top: 10px; font-family: monospace; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧪 AgoraProf LMS - Validation Report</h1>
        <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    
    <div class="summary">
        <h2>📊 Summary</h2>
        <div class="status">
            Overall Status: {'🎉 PASSED' if all(r['success'] for r in self.results.values()) else '❌ FAILED'}
        </div>
        <p>Total Validations: {len(self.results)}</p>
        <p>Passed: {sum(1 for r in self.results.values() if r['success'])}</p>
        <p>Failed: {sum(1 for r in self.results.values() if not r['success'])}</p>
    </div>
    
    <h2>🔍 Detailed Results</h2>
"""
        
        for name, result in self.results.items():
            css_class = 'passed' if result['success'] else 'failed'
            status_text = '✅ PASSED' if result['success'] else '❌ FAILED'
            
            html_content += f"""
    <div class="validation {css_class}">
        <h3>{name}</h3>
        <div class="status">{status_text}</div>
        <p>Duration: {result['duration']:.2f}s</p>
        
        {f'<div class="details"><h4>Error:</h4><pre>{result["error"]}</pre></div>' if result['error'] else ''}
        
        {f'<div class="details"><h4>Output:</h4><pre>{result["output"][:1000]}...</pre></div>' if result['output'] else ''}
    </div>
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"📄 HTML report generated: {filename}")
    
    def generate_json_report(self, filename='validation_report.json'):
        """Generate JSON validation report"""
        import json
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(self.results),
                'passed': sum(1 for r in self.results.values() if r['success']),
                'failed': sum(1 for r in self.results.values() if not r['success']),
                'overall_success': all(r['success'] for r in self.results.values())
            },
            'results': self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"📄 JSON report generated: {filename}")


def main():
    """Main validation runner"""
    print("🚀 Starting AgoraProf LMS Comprehensive Validation")
    print("=" * 80)
    
    # Run validations
    runner = ValidationRunner()
    success = runner.run_all_validations()
    
    # Generate reports
    report_generator = ValidationReportGenerator(runner.results)
    report_generator.generate_html_report()
    report_generator.generate_json_report()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
