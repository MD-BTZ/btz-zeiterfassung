#!/usr/bin/env python3
"""
Final comprehensive menu functionality validation script
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
import json

def setup_driver():
    """Setup Chrome WebDriver"""
    print("🔧 Setting up Chrome WebDriver for final validation...")
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ WebDriver initialized")
    return driver

def comprehensive_menu_test(driver):
    """Run comprehensive menu functionality tests"""
    print("🧪 Running comprehensive menu functionality tests...")
    
    test_results = {
        'console_errors': [],
        'dropdown_functionality': {},
        'navigation_tests': {},
        'responsive_behavior': {},
        'accessibility_features': {},
        'performance_metrics': {},
        'overall_score': 0
    }
    
    # Test 1: Console Error Detection
    print("\n📊 Test 1: Console Error Detection")
    logs = driver.get_log('browser')
    severe_errors = [log for log in logs if log['level'] == 'SEVERE']
    test_results['console_errors'] = severe_errors
    
    if len(severe_errors) == 0:
        print("  ✅ No severe console errors found")
        test_results['overall_score'] += 20
    else:
        print(f"  ❌ Found {len(severe_errors)} severe console errors")
        for error in severe_errors:
            print(f"    - {error['message']}")
    
    # Test 2: Dropdown Functionality
    print("\n🔽 Test 2: Dropdown Functionality")
    dropdown_toggles = driver.find_elements(By.CSS_SELECTOR, ".dropdown-toggle")
    test_results['dropdown_functionality'] = {
        'total_dropdowns': len(dropdown_toggles),
        'working_dropdowns': 0,
        'dropdown_details': []
    }
    
    for i, toggle in enumerate(dropdown_toggles):
        dropdown_name = toggle.text.strip()
        print(f"  Testing: {dropdown_name}")
        
        try:
            # Test hover functionality
            actions = ActionChains(driver)
            actions.move_to_element(toggle).perform()
            time.sleep(0.5)
            
            dropdown_menu = toggle.find_element(By.XPATH, "..//div[@class='dropdown-menu']")
            is_visible = dropdown_menu.is_displayed()
            
            dropdown_detail = {
                'name': dropdown_name,
                'hover_works': is_visible,
                'click_works': False,
                'items_count': 0
            }
            
            if is_visible:
                items = dropdown_menu.find_elements(By.CSS_SELECTOR, ".dropdown-item")
                dropdown_detail['items_count'] = len(items)
                print(f"    ✅ Hover: Working ({len(items)} items)")
                
                # Test click functionality
                toggle.click()
                time.sleep(0.3)
                dropdown_detail['click_works'] = dropdown_menu.is_displayed()
                
                test_results['dropdown_functionality']['working_dropdowns'] += 1
            else:
                print(f"    ❌ Hover: Not working")
            
            test_results['dropdown_functionality']['dropdown_details'].append(dropdown_detail)
            
            # Close dropdown
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.2)
            
        except Exception as e:
            print(f"    ❌ Error testing {dropdown_name}: {e}")
    
    # Calculate dropdown score
    dropdown_score = (test_results['dropdown_functionality']['working_dropdowns'] / 
                     test_results['dropdown_functionality']['total_dropdowns']) * 25
    test_results['overall_score'] += dropdown_score
    
    # Test 3: Navigation Links
    print("\n🔗 Test 3: Navigation Link Testing")
    nav_links = driver.find_elements(By.CSS_SELECTOR, "nav a")
    test_results['navigation_tests'] = {
        'total_links': len(nav_links),
        'working_links': 0,
        'link_details': []
    }
    
    for link in nav_links[:5]:  # Test first 5 links to avoid too much navigation
        try:
            href = link.get_attribute('href')
            text = link.text.strip()
            
            if href and href != 'javascript:void(0)' and href != '#':
                print(f"  Testing link: {text} -> {href}")
                
                # Check if link is accessible (doesn't return 404)
                original_url = driver.current_url
                link.click()
                time.sleep(1)
                
                # Check if page loaded successfully (no error page)
                page_title = driver.title
                is_error_page = 'error' in page_title.lower() or '404' in page_title
                
                link_detail = {
                    'text': text,
                    'href': href,
                    'accessible': not is_error_page,
                    'page_title': page_title
                }
                
                if not is_error_page:
                    test_results['navigation_tests']['working_links'] += 1
                    print(f"    ✅ Accessible: {page_title}")
                else:
                    print(f"    ❌ Error page: {page_title}")
                
                test_results['navigation_tests']['link_details'].append(link_detail)
                
                # Return to dashboard
                driver.get("http://127.0.0.1:8091/")
                time.sleep(1)
                
        except Exception as e:
            print(f"    ❌ Error testing link {text}: {e}")
    
    # Calculate navigation score
    nav_score = (test_results['navigation_tests']['working_links'] / 
                max(test_results['navigation_tests']['total_links'], 1)) * 20
    test_results['overall_score'] += nav_score
    
    # Test 4: Responsive Behavior
    print("\n📱 Test 4: Responsive Behavior")
    viewport_tests = [
        ("Desktop", 1920, 1080),
        ("Tablet", 768, 1024),
        ("Mobile", 375, 667)
    ]
    
    test_results['responsive_behavior'] = {
        'viewport_tests': [],
        'mobile_menu_works': False
    }
    
    for viewport_name, width, height in viewport_tests:
        driver.set_window_size(width, height)
        time.sleep(1)
        
        try:
            navbar = driver.find_element(By.CSS_SELECTOR, ".modern-navbar")
            is_responsive = navbar.is_displayed()
            
            # Test mobile menu toggle for mobile viewport
            mobile_menu_works = False
            if width <= 768:
                try:
                    mobile_toggle = driver.find_element(By.CSS_SELECTOR, ".mobile-menu-toggle")
                    if mobile_toggle.is_displayed():
                        mobile_toggle.click()
                        time.sleep(0.5)
                        
                        navbar_menu = driver.find_element(By.CSS_SELECTOR, ".navbar-menu")
                        mobile_menu_works = "active" in navbar_menu.get_attribute("class")
                        test_results['responsive_behavior']['mobile_menu_works'] = mobile_menu_works
                        
                        # Close mobile menu
                        mobile_toggle.click()
                        time.sleep(0.3)
                except:
                    pass
            
            viewport_result = {
                'name': viewport_name,
                'width': width,
                'height': height,
                'navbar_visible': is_responsive,
                'mobile_menu_works': mobile_menu_works if width <= 768 else None
            }
            
            test_results['responsive_behavior']['viewport_tests'].append(viewport_result)
            print(f"  {viewport_name} ({width}x{height}): {'✅' if is_responsive else '❌'}")
            
        except Exception as e:
            print(f"  ❌ Error testing {viewport_name}: {e}")
    
    # Reset to desktop view
    driver.set_window_size(1920, 1080)
    
    # Calculate responsive score
    responsive_score = 15 if all(vp['navbar_visible'] for vp in test_results['responsive_behavior']['viewport_tests']) else 0
    if test_results['responsive_behavior']['mobile_menu_works']:
        responsive_score += 5
    test_results['overall_score'] += responsive_score
    
    # Test 5: Accessibility Features
    print("\n♿ Test 5: Accessibility Features")
    accessibility_tests = []
    
    try:
        # Check for ARIA attributes
        aria_elements = driver.find_elements(By.CSS_SELECTOR, "[aria-expanded], [aria-hidden]")
        aria_score = len(aria_elements) > 0
        accessibility_tests.append(('ARIA attributes', aria_score))
        
        # Check for keyboard navigation support
        nav_links = driver.find_elements(By.CSS_SELECTOR, "nav a, nav button")
        keyboard_score = all(link.get_attribute('tabindex') != '-1' for link in nav_links[:3])
        accessibility_tests.append(('Keyboard navigation', keyboard_score))
        
        test_results['accessibility_features'] = {
            'aria_attributes': aria_score,
            'keyboard_navigation': keyboard_score
        }
        
        for test_name, passed in accessibility_tests:
            print(f"  {test_name}: {'✅' if passed else '❌'}")
        
        # Calculate accessibility score
        accessibility_score = sum(1 for _, passed in accessibility_tests) * 5
        test_results['overall_score'] += accessibility_score
        
    except Exception as e:
        print(f"  ❌ Error testing accessibility: {e}")
    
    return test_results

def generate_recommendations(test_results):
    """Generate recommendations based on test results"""
    recommendations = []
    
    if len(test_results['console_errors']) > 0:
        recommendations.append("Fix remaining console errors for better performance")
    
    if test_results['dropdown_functionality']['working_dropdowns'] < test_results['dropdown_functionality']['total_dropdowns']:
        recommendations.append("Investigate non-working dropdown menus")
    
    if test_results['navigation_tests']['working_links'] < test_results['navigation_tests']['total_links']:
        recommendations.append("Fix broken navigation links")
    
    if not all(vp['navbar_visible'] for vp in test_results['responsive_behavior']['viewport_tests']):
        recommendations.append("Improve responsive design for all viewport sizes")
    
    if not test_results['responsive_behavior']['mobile_menu_works']:
        recommendations.append("Fix mobile menu toggle functionality")
    
    if test_results['overall_score'] < 80:
        recommendations.append("Overall menu system needs improvement - consider additional testing and fixes")
    
    return recommendations

def main():
    """Main function to run comprehensive menu validation"""
    driver = setup_driver()
    
    try:
        # Login to the application
        print("🌐 Logging in to the application...")
        driver.get("http://127.0.0.1:8091/login")
        
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = driver.find_element(By.NAME, "password")
        
        username_field.send_keys("admin")
        password_field.send_keys("admin")
        
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for dashboard to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "nav")))
        time.sleep(2)
        print("✅ Successfully logged in")
        
        # Run comprehensive tests
        test_results = comprehensive_menu_test(driver)
        
        # Generate recommendations
        recommendations = generate_recommendations(test_results)
        test_results['recommendations'] = recommendations
        
        # Save detailed results
        with open('final_menu_validation.json', 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        # Print final summary
        print("\n" + "="*60)
        print("📊 FINAL MENU VALIDATION SUMMARY")
        print("="*60)
        print(f"Overall Score: {test_results['overall_score']:.1f}/100")
        print(f"Console Errors: {len(test_results['console_errors'])}")
        print(f"Working Dropdowns: {test_results['dropdown_functionality']['working_dropdowns']}/{test_results['dropdown_functionality']['total_dropdowns']}")
        print(f"Working Navigation: {test_results['navigation_tests']['working_links']}/{test_results['navigation_tests']['total_links']}")
        print(f"Responsive Viewports: {sum(1 for vp in test_results['responsive_behavior']['viewport_tests'] if vp['navbar_visible'])}/3")
        print(f"Mobile Menu: {'✅' if test_results['responsive_behavior']['mobile_menu_works'] else '❌'}")
        
        if recommendations:
            print("\n🔧 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec}")
        else:
            print("\n🎉 All tests passed! Menu functionality is excellent.")
        
        # Overall assessment
        score = test_results['overall_score']
        if score >= 90:
            assessment = "🌟 EXCELLENT - Menu system is fully functional"
        elif score >= 70:
            assessment = "✅ GOOD - Menu system works well with minor issues"
        elif score >= 50:
            assessment = "⚠️ FAIR - Menu system has some significant issues"
        else:
            assessment = "❌ POOR - Menu system needs major improvements"
        
        print(f"\n{assessment}")
        print("\n✅ Final validation completed!")
        print("📄 Detailed results saved to 'final_menu_validation.json'")
        
    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        
    finally:
        print("🔄 WebDriver closed")
        driver.quit()

if __name__ == "__main__":
    main()
