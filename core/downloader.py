import requests
import time
import os
import threading
import json
from concurrent.futures import ThreadPoolExecutor
from utils.helpers import format_time

def download_segment(url, start, end, part_file, download_info, update_queue, lock):
    try:
        # Self-heal previously corrupted files (bug fix for >100% progress)
        expected_max_size = end - start + 1
        current_start = start
        if os.path.exists(part_file):
            current_size = os.path.getsize(part_file)
            if current_size > expected_max_size:
                with open(part_file, 'r+b') as f:
                    f.truncate(expected_max_size)
                current_size = expected_max_size
            current_start = start + current_size
            
        if current_start > end:
            return True # Segment already finished

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Range': f'bytes={current_start}-{end}'
        }
        response = requests.get(url, stream=True, headers=headers, timeout=(15, 30))
        
        # 206 is Partial Content, 200 is also fine if it's the whole file
        if response.status_code == 403:
            raise Exception("Access Forbidden (Link Expired?). Please update URL.")
        if response.status_code not in [200, 206]:
            raise Exception(f"Server error: {response.status_code}")
            
        # If server ignores Range and sends whole file from start, but we wanted a segment
        if response.status_code == 200 and current_start > 0:
            raise Exception("Server ignored Range request. Resuming failed.")

        # mode = 'ab' if current_start > start else 'wb'
        # Crucial fix: ONLY use 'wb' if the file is truly empty or doesn't exist AND we are starting from the absolute beginning
        if os.path.exists(part_file) and os.path.getsize(part_file) > 0:
            mode = 'ab'
        else:
            mode = 'wb'
            
        # Diagnostic print to terminal (visible to user in console)
        print(f"[DEBUG] Part {part_file}: Mode={mode}, Start={start}, Current={current_start}, End={end}")
        bytes_to_read = end - current_start + 1
        run_id = download_info.get('run_id')
        
        with open(part_file, mode) as f:
            local_downloaded = 0
            for chunk in response.iter_content(chunk_size=128 * 1024): # 128KB chunks
                if download_info.get('paused', False) or (run_id and download_info.get('run_id') != run_id):
                    return False
                
                if chunk:
                    try:
                        # Enforce reading limits strictly
                        if local_downloaded + len(chunk) > bytes_to_read:
                            chunk = chunk[:bytes_to_read - local_downloaded]
                        
                        f.write(chunk)
                        chunk_len = len(chunk)
                        local_downloaded += chunk_len
                        
                        with lock:
                            download_info['downloaded'] += chunk_len
                            
                        # If we have reached our limit for this segment, stop safely
                        if local_downloaded >= bytes_to_read:
                            break
                    except Exception as e:
                        raise e
            
        return True
    except requests.exceptions.RequestException as e:
        with lock:
            if not download_info.get('paused'):
                download_info['status'] = 'Paused (Connection Lost)'
                download_info['paused'] = True
        return False
    except Exception as e:
        with lock:
            if not download_info.get('paused'):
                download_info['status'] = f'Segment Error: {str(e)}'
                # Don't necessarily pause everything on general errors, but could
        return False

def perform_download(download_info, update_queue):
    try:
        # ABSOLUTE DEBUG: If you don't see this, the function is NOT being called
        print(f"\n{'='*20} STARTING DOWNLOAD ID: {download_info.get('id')} {'='*20}")
        print(f"URL: {download_info.get('url')}")
        
        url = download_info['url']
        save_path = download_info['save_path']
        total_size = download_info['total_size']
        download_id = download_info['id']
        lock = threading.Lock()
        
        # Define standard headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # Domain-specific optimizations
        is_gdrive = "drive.google.com" in url or "docs.google.com" in url
        
        # Check if server supports Range requests (multi-thread)
        # Use existing hint if available to skip redundant pings
        supports_range = download_info.get('supports_range', False)
        
        if not supports_range:
            try:
                head = requests.head(url, allow_redirects=True, timeout=10, headers=headers)
                supports_range = 'bytes' in head.headers.get('Accept-Ranges', '') or head.status_code == 206
                
                # If HEAD fails to confirm, try a small GET range request (more reliable)
                if not supports_range:
                    range_headers = headers.copy()
                    range_headers['Range'] = 'bytes=0-0'
                    r = requests.get(url, headers=range_headers, stream=True, timeout=10)
                    supports_range = (r.status_code == 206)
                    r.close()
            except:
                supports_range = False

        print(f"[DEBUG] Range Support Detection: {supports_range}")

        # Ensure downloaded starts correctly from existing data
        if 'downloaded' not in download_info or download_info['downloaded'] is None:
            download_info['downloaded'] = 0
        
        # RECALCULATE FROM DISK (FOLDER .parts)
        temp_dir = save_path + ".parts"
        initial_downloaded = 0
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                if f.startswith("part"):
                    try:
                        initial_downloaded += os.path.getsize(os.path.join(temp_dir, f))
                    except: pass
            
        print(f"[DEBUG] Total size found on disk (.parts): {initial_downloaded}")
        
        # If it's a resume but memory says 0, use disk value
        if download_info['downloaded'] == 0:
            download_info['downloaded'] = initial_downloaded
            
        print(f"[DEBUG] Final Initial Downloaded count: {download_info['downloaded']}")

        # CHECK IF WE ALREADY HAVE MULTI-THREAD DATA
        was_multi = download_info.get('threads', 1) > 1
        
        # If we previously used multi-threads but now server says no range support, it's a problem
        if was_multi and not supports_range:
            # If we already have some data on disk, we CANNOT fallback to single thread (it will restart 0%)
            if initial_downloaded > 0:
                print(f"[DEBUG] FATAL: Multi-thread was used before, but server now refuses Range. Stopping.")
                raise Exception("Server no longer supports resume (Link Expired?). Please update the URL.")

        if total_size <= 0:
            # Try to get size again if it's missing
            try:
                if not head:
                    head = requests.head(url, allow_redirects=True, timeout=10, headers=headers)
                total_size = int(head.headers.get('content-length', 0))
                download_info['total_size'] = total_size
            except:
                pass

        # Multi-thread only if supported, size > 1MB
        # GDrive optimization: Limit threads to 2 to avoid "Too many requests" (429)
        if download_info.get('threads'):
            num_threads = download_info['threads']
        else:
            if is_gdrive:
                num_threads = 2 if (supports_range and total_size > 1024 * 1024) else 1
            else:
                num_threads = 8 if (supports_range and total_size > 1024 * 1024) else 1
            download_info['threads'] = num_threads # Save it for future resumes
        
        print(f"[DEBUG] Domain: {'GDrive' if is_gdrive else 'Generic'}, Threads: {num_threads}")
        if num_threads > 1:
            # DEBUG: Log segment state
            seg_status = "FOUND" if download_info.get('segments') else "MISSING"
            print(f"[DEBUG] Segment Data in Memory: {seg_status}")
            print(f"[DEBUG] Multi-threading: {supports_range}, Threads: {num_threads}")
            
            download_info['status'] = f'Downloading ({num_threads} threads)...'
            update_queue.put(('update', download_id))
            
            # Temporary directory for segments
            temp_dir = save_path + ".parts"
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            # CRITICAL: Calculate initial downloaded bytes from existing parts to prevent UI 0% reset
            initial_downloaded = 0
            if os.path.exists(temp_dir):
                for i in range(num_threads):
                    pf = os.path.join(temp_dir, f"part{i}")
                    if os.path.exists(pf):
                        initial_downloaded += os.path.getsize(pf)
            
            # Use the already calculated initial_downloaded
            with lock:
                download_info['downloaded'] = initial_downloaded
                if total_size > 0:
                    download_info['progress'] = (initial_downloaded / total_size) * 100
            
            update_queue.put(('update', download_id)) # Immediate UI update to show resume position

            # COORDINATE LOCKING: Calculate segments only if they don't exist
            segments = []
            if download_info.get('segments'):
                try:
                    segments = json.loads(download_info['segments'])
                except:
                    segments = []

            if not segments:
                segment_size = total_size // num_threads
                for i in range(num_threads):
                    start = i * segment_size
                    end = (total_size - 1) if (i == num_threads - 1) else ((i + 1) * segment_size - 1)
                    segments.append({'index': i, 'start': start, 'end': end})
                
                # Save fixed coordinates to database
                download_info['segments'] = json.dumps(segments)
                from utils.database import save_download
                save_download(download_info)

            # Verification for user: log that we are using fixed segments
            if segments:
                count = len(segments)
                download_info['status'] = f'Resuming {count} segments...'
                update_queue.put(('update', download_id))

            futures = []
            part_files = []
            
            # Use run_id to safely orphan lingering background threads from previous resumes
            run_id = time.time()
            download_info['run_id'] = run_id
            
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                for seg in segments:
                    i = seg['index']
                    start = seg['start']
                    end = seg['end']
                    
                    part_file = os.path.join(temp_dir, f"part{i}")
                    part_files.append(part_file)
                    
                    futures.append(executor.submit(download_segment, url, start, end, part_file, download_info, update_queue, lock))
                
                # Monitor progress
                start_time = time.time()
                last_update = start_time
                last_downloaded = 0
                
                while any(f.running() for f in futures):
                    if download_info.get('paused', False) or download_info.get('run_id') != run_id:
                        executor.shutdown(wait=False, cancel_futures=True)
                        if download_info.get('run_id') == run_id:
                            download_info['status'] = 'Paused'
                        update_queue.put(('update', download_id))
                        return # Paused, cleanup happens on restart or manual

                    current_time = time.time()
                    if current_time - last_update >= 0.5:
                        with lock:
                            current_downloaded = download_info['downloaded']
                        
                        speed = (current_downloaded - last_downloaded) / (current_time - last_update)
                        download_info['speed'] = speed
                        download_info['progress'] = (current_downloaded / total_size) * 100 if total_size > 0 else 0
                        
                        # Calculate ETA and Elapsed
                        elapsed = current_time - download_info['start_time']
                        download_info['elapsed_time'] = format_time(elapsed)
                        
                        if speed > 0 and total_size > 0:
                            eta_seconds = (total_size - current_downloaded) / speed
                            download_info['eta'] = format_time(eta_seconds)
                        # else:
                        #     download_info['eta'] = "--:--"
                        
                        update_queue.put(('update', download_id))
                        
                        last_update = current_time
                        last_downloaded = current_downloaded
                    
                    time.sleep(0.1)

                segment_results = []
                for f in futures:
                    try:
                        res = f.result()
                        segment_results.append(res)
                    except Exception as e:
                        print(f"[DEBUG] Segment Exception: {str(e)}")
                        segment_results.append(False)

                if not all(segment_results):
                    if not download_info.get('paused'):
                        download_info['status'] = 'Paused (Error in segments)'
                        download_info['paused'] = True
                    update_queue.put(('update', download_id))
                    return

            # MERGING with Buffer (Safe for large files)
            download_info['status'] = 'Merging...'
            update_queue.put(('update', download_id))
            update_queue.put(('update', download_id))
            
            try:
                with open(save_path, 'wb') as final_file:
                    merged_bytes = 0
                    last_ui_update = time.time()
                    for part_file in part_files:
                        if os.path.exists(part_file):
                            with open(part_file, 'rb') as pf:
                                while True:
                                    chunk = pf.read(1024 * 1024 * 4) # 4MB Buffer for faster merge
                                    if not chunk:
                                        break
                                    final_file.write(chunk)
                                    merged_bytes += len(chunk)
                                    
                                    # Update UI during merge for very large files
                                    current_time = time.time()
                                    if current_time - last_ui_update > 0.5:
                                        merge_pct = (merged_bytes / total_size * 100) if total_size > 0 else 0
                                        download_info['status'] = f'Merging... {int(merge_pct)}%'
                                        update_queue.put(('update', download_id))
                                        last_ui_update = current_time
                            os.remove(part_file)
                
                # Remove temp directory
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except Exception as e:
                download_info['status'] = f"Merging Error: {str(e)}"
                update_queue.put(('update', download_id))
                return
            
            download_info['status'] = 'Completed'
            download_info['progress'] = 100
            update_queue.put(('update', download_id))
            update_queue.put(('complete', download_id))
            
        else:
            # Fallback to single thread (old way) or if it's too small
            # (Reuse existing single-thread code for robustness)
            
            # Diagnostic for User
            if not supports_range:
                print(f"[DEBUG] Server does not support resume. Status will be 'Resume not supported'.")
                download_info['status'] = 'Downloading (Resume not supported)...'
                update_queue.put(('update', download_id))

            # Use headers (User-Agent) for everything
            if download_info.get('resume_pos', 0) > 0 and os.path.exists(save_path):
                headers['Range'] = f"bytes={download_info['resume_pos']}-"
            
            response = requests.get(url, stream=True, headers=headers, timeout=(15, 30))
            
            # If server doesn't support range for the resume, we must restart
            if download_info.get('resume_pos', 0) > 0 and response.status_code != 206:
                download_info['downloaded'] = 0
                download_info['resume_pos'] = 0
                mode = 'wb'
            else:
                mode = 'ab' if response.status_code == 206 else 'wb'
                if mode == 'wb': download_info['downloaded'] = 0
                else: download_info['downloaded'] = download_info.get('resume_pos', 0)
            
            with open(save_path, mode) as f:
                last_update = time.time()
                bytes_since_last = 0
                for chunk in response.iter_content(chunk_size=128 * 1024): # 128KB chunks
                    if download_info.get('paused'):
                        download_info['resume_pos'] = download_info['downloaded']
                        download_info['status'] = 'Paused'
                        update_queue.put(('update', download_id))
                        return
                    if chunk:
                        f.write(chunk)
                        download_info['downloaded'] += len(chunk)
                        bytes_since_last += len(chunk)
                        
                        # Update total size if it was unknown
                        if total_size <= 0 and 'content-length' in response.headers:
                            try:
                                total_size = int(response.headers['content-length'])
                                download_info['total_size'] = total_size
                            except: pass

                        curr_time = time.time()
                        if curr_time - last_update >= 0.5:
                            download_info['speed'] = bytes_since_last / (curr_time - last_update)
                            download_info['progress'] = (download_info['downloaded'] / total_size) * 100 if total_size > 0 else 0
                            
                            # Calculate ETA and Elapsed for single thread
                            elapsed = curr_time - download_info['start_time']
                            download_info['elapsed_time'] = format_time(elapsed)
                            
                            if download_info['speed'] > 0 and total_size > 0:
                                eta_seconds = (total_size - download_info['downloaded']) / download_info['speed']
                                download_info['eta'] = format_time(eta_seconds)
                            # else:
                            #     download_info['eta'] = "--:--"
                                
                            update_queue.put(('update', download_id))
                            last_update = curr_time
                            bytes_since_last = 0
                            
            download_info['status'] = 'Completed'
            download_info['progress'] = 100
            update_queue.put(('update', download_id))
            update_queue.put(('complete', download_id))

    except requests.exceptions.RequestException as e:
        download_info['resume_pos'] = download_info.get('downloaded', 0)
        download_info['status'] = 'Paused (Connection Lost)'
        download_info['paused'] = True
        update_queue.put(('update', download_id))
    except Exception as e:
        download_info['status'] = f'Error: {str(e)}'
        download_info['paused'] = True
        update_queue.put(('update', download_id))

