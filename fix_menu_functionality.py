#!/usr/bin/env python3
"""
JavaScript error detection and menu functionality fix script
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
    """Setup Chrome WebDriver with console logging"""
    print("🔧 Setting up Chrome WebDriver for error detection...")
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Enable logging to capture JavaScript errors
    chrome_options.add_argument("--enable-logging")
    chrome_options.add_argument("--log-level=0")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("✅ WebDriver initialized with logging")
    return driver

def capture_console_errors(driver):
    """Capture JavaScript console errors"""
    print("🔍 Capturing console errors...")
    
    # Get console logs
    logs = driver.get_log('browser')
    errors = []
    
    for log in logs:
        if log['level'] in ['SEVERE', 'WARNING']:
            errors.append({
                'level': log['level'],
                'message': log['message'],
                'source': log.get('source', 'Unknown'),
                'timestamp': log.get('timestamp', 0)
            })
    
    print(f"Found {len(errors)} console errors/warnings")
    return errors

def test_dropdown_functionality(driver):
    """Test dropdown functionality with different approaches"""
    print("\n🔽 Testing dropdown functionality...")
    
    results = {
        'dropdowns_found': 0,
        'working_dropdowns': 0,
        'failed_dropdowns': [],
        'working_methods': []
    }
    
    # Find all dropdown toggles
    dropdown_toggles = driver.find_elements(By.CSS_SELECTOR, ".dropdown-toggle")
    results['dropdowns_found'] = len(dropdown_toggles)
    
    print(f"Found {len(dropdown_toggles)} dropdown toggles")
    
    for i, toggle in enumerate(dropdown_toggles):
        try:
            dropdown_name = toggle.text.strip()
            print(f"  Testing dropdown {i+1}: '{dropdown_name}'")
            
            # Get the parent dropdown container
            dropdown_container = toggle.find_element(By.XPATH, "./..")
            dropdown_menu = dropdown_container.find_element(By.CSS_SELECTOR, ".dropdown-menu")
            
            # Test hover activation (desktop)
            actions = ActionChains(driver)
            actions.move_to_element(toggle).perform()
            time.sleep(0.5)
            
            # Check if dropdown opened
            is_visible_hover = dropdown_menu.is_displayed()
            
            # Test click activation
            toggle.click()
            time.sleep(0.5)
            
            # Check if dropdown opened after click
            is_visible_click = dropdown_menu.is_displayed()
            
            # Check aria-expanded attribute
            aria_expanded = toggle.get_attribute('aria-expanded')
            
            success = is_visible_hover or is_visible_click or aria_expanded == 'true'
            
            print(f"    Hover: {is_visible_hover}, Click: {is_visible_click}, ARIA: {aria_expanded}")
            
            if success:
                results['working_dropdowns'] += 1
                if is_visible_hover:
                    results['working_methods'].append(f"{dropdown_name}: hover")
                if is_visible_click:
                    results['working_methods'].append(f"{dropdown_name}: click")
            else:
                results['failed_dropdowns'].append(dropdown_name)
            
            # Close dropdown by clicking elsewhere
            driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(0.3)
            
        except Exception as e:
            print(f"    ❌ Error testing dropdown {i+1}: {e}")
            results['failed_dropdowns'].append(f"Dropdown {i+1}: {str(e)}")
    
    return results

def fix_dropdown_functionality(driver):
    """Inject JavaScript to fix dropdown functionality"""
    print("\n🔧 Attempting to fix dropdown functionality...")
    
    fix_script = """
    // Fix dropdown functionality
    function fixDropdowns() {
        console.log('Fixing dropdown functionality...');
        
        const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
        console.log('Found ' + dropdownToggles.length + ' dropdown toggles');
        
        dropdownToggles.forEach((toggle, index) => {
            const dropdown = toggle.closest('.dropdown, .nav-item');
            const menu = dropdown ? dropdown.querySelector('.dropdown-menu') : null;
            
            if (!menu) {
                console.log('No menu found for toggle', index);
                return;
            }
            
            // Remove existing event listeners to avoid conflicts
            toggle.replaceWith(toggle.cloneNode(true));
            const newToggle = dropdown.querySelector('.dropdown-toggle');
            
            // Add hover functionality for desktop
            dropdown.addEventListener('mouseenter', function() {
                if (window.innerWidth > 768) {
                    newToggle.setAttribute('aria-expanded', 'true');
                    menu.style.opacity = '1';
                    menu.style.visibility = 'visible';
                    menu.style.transform = 'translateY(0)';
                    menu.style.display = 'block';
                }
            });
            
            dropdown.addEventListener('mouseleave', function() {
                if (window.innerWidth > 768) {
                    newToggle.setAttribute('aria-expanded', 'false');
                    menu.style.opacity = '0';
                    menu.style.visibility = 'hidden';
                    menu.style.transform = 'translateY(-0.5rem)';
                    setTimeout(() => {
                        if (menu.style.opacity === '0') {
                            menu.style.display = 'none';
                        }
                    }, 200);
                }
            });
            
            // Add click functionality for mobile
            newToggle.addEventListener('click', function(e) {
                e.preventDefault();
                
                const isExpanded = newToggle.getAttribute('aria-expanded') === 'true';
                
                // Close all other dropdowns
                document.querySelectorAll('.dropdown-toggle').forEach(otherToggle => {
                    if (otherToggle !== newToggle) {
                        otherToggle.setAttribute('aria-expanded', 'false');
                        const otherMenu = otherToggle.closest('.dropdown, .nav-item').querySelector('.dropdown-menu');
                        if (otherMenu) {
                            otherMenu.style.opacity = '0';
                            otherMenu.style.visibility = 'hidden';
                            otherMenu.style.transform = 'translateY(-0.5rem)';
                            otherMenu.style.display = 'none';
                        }
                    }
                });
                
                // Toggle current dropdown
                if (isExpanded) {
                    newToggle.setAttribute('aria-expanded', 'false');
                    menu.style.opacity = '0';
                    menu.style.visibility = 'hidden';
                    menu.style.transform = 'translateY(-0.5rem)';
                    setTimeout(() => menu.style.display = 'none', 200);
                } else {
                    newToggle.setAttribute('aria-expanded', 'true');
                    menu.style.display = 'block';
                    menu.style.opacity = '1';
                    menu.style.visibility = 'visible';
                    menu.style.transform = 'translateY(0)';
                }
            });
            
            console.log('Fixed dropdown', index, newToggle.textContent.trim());
        });
        
        // Close dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.dropdown, .nav-item')) {
                document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
                    toggle.setAttribute('aria-expanded', 'false');
                    const menu = toggle.closest('.dropdown, .nav-item').querySelector('.dropdown-menu');
                    if (menu) {
                        menu.style.opacity = '0';
                        menu.style.visibility = 'hidden';
                        menu.style.transform = 'translateY(-0.5rem)';
                        menu.style.display = 'none';
                    }
                });
            }
        });
        
        console.log('Dropdown functionality fixed!');
        return true;
    }
    
    return fixDropdowns();
    """
    
    try:
        result = driver.execute_script(fix_script)
        print(f"✅ Dropdown fix script executed: {result}")
        return True
    except Exception as e:
        print(f"❌ Error executing fix script: {e}")
        return False

def main():
    """Main function to test and fix menu functionality"""
    driver = setup_driver()
    
    try:
        # Navigate to login page first
        print("🌐 Loading login page...")
        driver.get("http://127.0.0.1:8091/login")
        time.sleep(2)
        
        # Capture initial console errors
        login_errors = capture_console_errors(driver)
        
        # Login to the application
        print("🔐 Logging in...")
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        
        username_field.send_keys("admin")
        password_field.send_keys("admin")
        
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()
        
        # Wait for dashboard to load
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "nav")))
        time.sleep(2)
        
        # Capture post-login console errors
        dashboard_errors = capture_console_errors(driver)
        
        # Test current dropdown functionality
        print("\n📊 Testing current dropdown functionality...")
        dropdown_results = test_dropdown_functionality(driver)
        
        # Apply dropdown fixes
        fix_success = fix_dropdown_functionality(driver)
        
        if fix_success:
            # Test dropdown functionality after fix
            print("\n🔄 Testing dropdown functionality after fix...")
            fixed_results = test_dropdown_functionality(driver)
            
            # Compare results
            print(f"\n📈 Improvement Report:")
            print(f"  Before fix: {dropdown_results['working_dropdowns']}/{dropdown_results['dropdowns_found']} working")
            print(f"  After fix:  {fixed_results['working_dropdowns']}/{fixed_results['dropdowns_found']} working")
        
        # Save comprehensive results
        test_results = {
            'console_errors': {
                'login_page': login_errors,
                'dashboard_page': dashboard_errors
            },
            'dropdown_functionality': {
                'before_fix': dropdown_results,
                'after_fix': fixed_results if fix_success else None,
                'fix_applied': fix_success
            },
            'recommendations': []
        }
        
        # Generate recommendations
        if len(login_errors) > 0:
            test_results['recommendations'].append("Fix JavaScript errors on login page")
        
        if len(dashboard_errors) > 0:
            test_results['recommendations'].append("Fix JavaScript errors on dashboard page")
        
        if dropdown_results['working_dropdowns'] < dropdown_results['dropdowns_found']:
            test_results['recommendations'].append("Apply dropdown functionality fixes")
        
        # Save results
        with open('menu_error_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        print("\n📊 Final Test Summary:")
        print(f"  Login page errors: {len(login_errors)}")
        print(f"  Dashboard page errors: {len(dashboard_errors)}")
        print(f"  Dropdown functionality: {dropdown_results['working_dropdowns']}/{dropdown_results['dropdowns_found']}")
        print(f"  Fix applied successfully: {fix_success}")
        
        if fix_success and fixed_results:
            print(f"  Post-fix dropdown functionality: {fixed_results['working_dropdowns']}/{fixed_results['dropdowns_found']}")
        
        print("\n✅ Menu error analysis completed!")
        print("📄 Results saved to 'menu_error_analysis.json'")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        
    finally:
        print("🔄 WebDriver closed")
        driver.quit()

if __name__ == "__main__":
    main()
