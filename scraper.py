from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
import csv
import time
import random
import json

from urllib.parse import urlparse, urljoin


def setup_driver():
    """
    Set up and configure a Chrome WebDriver instance for web scraping.
    Returns:
      WebDriver: The configured Chrome WebDriver instance.
    """

    chrome_options = Options()
    chrome_options.add_argument(
        "--headless"
    )  # for debugging purposes. UPDATE: removing this may cause an error where the load more button can not be found.
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )

    service = Service(r"C:\WebDrivers\chromedriver.exe")  # Change path if needed
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def is_allowed(url):
    """
    Check if a given URL is allowed based on the path.
    Args:
      url (str): The URL to be checked.
    Returns:
      bool: True if the URL is allowed, False otherwise.
    """

    parsed_url = urlparse(url)
    path = parsed_url.path

    # Disallowed paths according to the website's robot.txt file
    disallowed_paths = [
        "/my/en/cms/",
        "/my/en/search",
        "/my/en/news/search",
        "/my/en/news/sp/search",
    ]

    return not any(path.startswith(disallowed) for disallowed in disallowed_paths)


def scroll_and_click_load_more(driver):
    """
    Scroll to the bottom of the page and click 'Load more' button
    to load more products
    """

    load_more_count = 0

    load_more_xpath = (
        "//a[@href='#' and @target='_self'][.//div[contains(@class, 'fr-load-more')]]"
    )

    # TODO - Something wrong with the xpath of the anchor tag for the load more button
    # Maybe change the xpath would fix this issue

    while True:
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )  # Scroll to bottom of page
        time.sleep(random.uniform(2, 4))

        print(
            f"Current page height: {driver.execute_script('return document.body.scrollHeight')}"
        )

        try:
            load_more_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, load_more_xpath))
            )
            print(f"Load more button found: {load_more_button.is_displayed()}")

            if not load_more_button.is_displayed():
                print("Load more button is not visible")
                break

            driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
            time.sleep(random.uniform(1, 2))
            load_more_button.click()
            load_more_count += 1
            print(f"Clicked 'Load more' button {load_more_count} times")
            time.sleep(random.uniform(2, 4))

        except TimeoutException:
            print("Timeout waiting for 'Load more' button")
            break
        except NoSuchElementException:
            print("'Load more' button not found")
            break
        except StaleElementReferenceException:
            print("Page structure changed, retrying...")
            time.sleep(random.uniform(1, 2))
            continue
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            break

        print(
            f"Finished loading more products. Clicked {load_more_count} times in total."
        )


def extract_product_info(product, base_url):
    """
    Extracts information about a product from a web page.
    Args:
      product: WebElement object representing the product.
      base_url: Base URL of the web page.
    Returns:
      A dictionary containing the extracted product information, including:
      - product_id: ID of the product.
      - title: Title of the product.
      - image: URL of the product image.
      - color_options: Number of color options available for the product.
      - size_info: Size information of the product.
      - original_price: Original price of the product.
      - sale_price: Sale price of the product.
      - discount: Discount percentage of the product.
      - limited_offer: Limited offer status of the product.
      - additional_info: Additional information about the product.
      - product_url: URL of the product page.
    """

    try:
        product_id = product.get_attribute("data-test").split("product-card-")[-1]
        image = product.find_element(
            By.CSS_SELECTOR, ".fr-product-image img"
        ).get_attribute("src")

        # Color options (accounting for "extra" option)
        color_tips = product.find_elements(By.CSS_SELECTOR, ".color-tips .color-tip")
        color_options = sum(
            1 for tip in color_tips if "extra" not in tip.get_attribute("class")
        )

        title = product.find_element(By.CSS_SELECTOR, "h2.description").text.strip()

        # Size information
        size_info = product.find_element(
            By.CSS_SELECTOR, '[data-test="product-card-size"]'
        ).text.strip()

        price_element = product.find_element(By.CSS_SELECTOR, ".fr-product-price")

        # Price extraction (handling both original and limited price)
        original_price = None
        sale_price = None

        original_price_element = price_element.find_elements(
            By.CSS_SELECTOR, ".price-original .fr-price-currency span"
        )
        if original_price_element:
            original_price = original_price_element[-1].text.strip()

        limited_price_element = price_element.find_elements(
            By.CSS_SELECTOR, ".price-limited .fr-price-currency span"
        )
        if limited_price_element:
            sale_price = limited_price_element[-1].text.strip()

        if not sale_price:
            sale_price = None

        # Discount calculation
        discount = None
        if original_price and sale_price:
            try:
                original_price_float = float(
                    original_price.replace(",", "").replace("RM", "")
                )
                sale_price_float = float(sale_price.replace(",", "").replace("RM", ""))
                discount = round(
                    (original_price_float - sale_price_float)
                    / original_price_float
                    * 100,
                    2,
                )
            except ValueError:
                print(
                    f"Error converting prices to float: original_price={original_price}, sale_price={sale_price}"
                )

        # Limited offer extraction
        limited_offer = product.find_elements(
            By.CSS_SELECTOR, ".fr-status-flag-text[data-test^='limited-offer-from']"
        )
        limited_offer = limited_offer[0].text.strip() if limited_offer else None

        # Additional product information (may not be needed!)
        additional_info = product.find_elements(By.CSS_SELECTOR, "ul.fr-status-flag li")
        additional_info = [
            info.text.strip()
            for info in additional_info
            if "limited-offer" not in info.get_attribute("data-test")
        ]

        product_url = urljoin(
            base_url, product.find_element(By.CSS_SELECTOR, "a").get_attribute("href")
        )

        if not is_allowed(product_url):
            print(f"Skipping disallowed URL: {product_url}")
            return None

        product_info = {
            "product_id": product_id,
            "title": title,
            "image": image,
            "color_options": color_options,
            "size_info": size_info,
            "original_price": original_price,
            "sale_price": sale_price,
            "discount": f"{discount}%" if discount is not None else None,
            "limited_offer": limited_offer,
            "additional_info": additional_info,
            "product_url": product_url,
        }

        print(f"Extracted product info: {product_info}")  # Sanity check
        return product_info

    except Exception as e:
        print(f"Error extracting product info: {str(e)}")
        return None


def scrape_uniqlo_women_tops(url):
    """
    Scrapes the Uniqlo website for women's tops using the provided URL.
    Args:
      url (str): The URL of the Uniqlo website to scrape.
    Returns:
      list: A list of dictionaries containing information about the scraped products.
    """
    pass

    if not is_allowed(url):
        print("Not allowed to scrape")
        return []

    driver = setup_driver()
    driver.get(url)
    print(f"Navigated to... {url}")  # Sanity check

    time.sleep(10)

    print(
        f"Initial page height: {driver.execute_script('return document.body.scrollHeight')}"
    )
    print(
        f"Page title: {driver.title}"
    )  # This will help confirm if the page loaded correctly

    scroll_and_click_load_more(driver)  # Load all products before extracting it

    product_list = driver.find_elements(By.CSS_SELECTOR, "article.fr-grid-item.w4")
    print(f"Found {len(product_list)} products")  # Sanity check

    products = []
    for i, product in enumerate(product_list, 1):
        product_info = extract_product_info(product, url)
        if product_info:
            products.append(product_info)
        print(f"Processed product {i}/{len(product_list)}")  # Sanity check

    driver.quit()
    print("Driver closed")  # Sanity check

    return products


def save_to_csv(products, filename):
    """
    Save a list of products to a CSV file.
    Args:
      products (list): A list of dictionaries representing products.
      filename (str): The name of the CSV file to save.
    """

    if not products:
        print("No products to save.")
        return

    keys = products[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(products)
    print(f"Saved {len(products)} products to {filename}")  # Sanity check


def save_to_json(products, filename):
    """
    Save a list of products to a JSON file.
    Args:
      products (list): A list of dictionaries representing products.
      filename (str): The name of the JSON file to save.
    """
    if not products:
        print("No products to save.")
        return

    with open(filename, "w", encoding="utf-8") as output_file:
        json.dump(products, output_file, ensure_ascii=False, indent=4)
    print(f"Saved {len(products)} products to {filename}")  # Sanity check


if __name__ == "__main__":
    url = "https://www.uniqlo.com/my/en/women/tops/tops-collections"
    products = scrape_uniqlo_women_tops(url)
    save_to_csv(products, "uniqlo_women_tops.csv")
    print(f"Scraped {len(products)} products and saved to uniqlo_women_tops.csv")

    save_to_json(products, "uniqlo_women_tops.json")
    print(f"Scraped {len(products)} products and saved to uniqlo_women_tops.json")

    # Final sanity checks
    assert len(products) > 0, "No products were scraped"
    assert all(
        "product_id" in p for p in products
    ), "Some products are missing product_id"
    assert all("title" in p for p in products), "Some products are missing title"
    assert all("image" in p for p in products), "Some products are missing image URL"
    print("All sanity checks passed")
