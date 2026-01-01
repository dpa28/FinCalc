import requests
import logging
import time
import os
import app_state

class SafeRequest:
    @staticmethod
    def get(url, params=None, timeout=10, retries=3):
        """
        Fetches data with exponential backoff retry logic.
        """
        for i in range(retries):
            start_time = time.time()
            try:
                if app_state.debug_mode:
                    logging.info(f"REQ (Try {i+1}/{retries}) -> {url} | Params: {params}")

                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                
                if app_state.debug_mode:
                    duration = (time.time() - start_time) * 1000
                    logging.info(f"RES <- {response.status_code} ({duration:.0f}ms)")

                return response.json()

            except requests.exceptions.Timeout:
                logging.warning(f"Timeout connecting to {url}. Retrying...")
            except requests.exceptions.RequestException as e:
                # 429 = Rate Limit. Wait longer.
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    logging.warning("Rate limit hit. Cooling down...")
                    time.sleep(2 ** (i + 2)) # Extra wait for rate limits
                else:
                    logging.error(f"Network Error: {e}")
            except ValueError:
                logging.error("Error decoding JSON response")
                return None
            
            # Exponential Backoff: Wait 1s, 2s, 4s...
            if i < retries - 1:
                time.sleep(2 ** i)
        
        return None

    @staticmethod
    def download_image(url, filename):
        if os.path.exists(filename):
            if app_state.debug_mode: logging.info(f"CACHE HIT -> {filename}")
            return True

        try:
            if app_state.debug_mode:
                logging.info(f"IMG -> {url}")
            response = requests.get(url, stream=True, timeout=5)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
        except Exception as e:
            logging.error(f"Image Download Error: {e}")
        return False