import io
import os
import subprocess
import tempfile
import sys
import logging
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from src.utils.config_manager import ConfigManager

# Setup thread-safe logging for PDF/Preview generation
logger = logging.getLogger("PreviewGenerator")
if not logger.handlers:
    try:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        os.makedirs(log_dir, exist_ok=True)
        handler = logging.FileHandler(os.path.join(log_dir, "pdf_generation.log"), encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    except:
        pass # Fallback to no logging if folder is read-only

class PreviewGenerator:
    """
    [STABILIZATION] Sandboxed Preview Generator.
    This class acts as a proxy to an isolated worker process.
    NO native rendering libraries (weasyprint, fitz) are imported here.
    """

    @staticmethod
    def _is_enabled():
        """Check if rendering is enabled in settings"""
        # [Stabilization] Enable by default now that hardening is complete
        return ConfigManager().get_setting('render_enabled', True)

    @staticmethod
    def _get_worker_path():
        """Get absolute path to the render worker script"""
        return os.path.join(os.path.dirname(os.path.dirname(__file__)), "services", "render_worker.py")

    @staticmethod
    def generate_preview_image(html_content, width=None, all_pages=False):
        """
        Spawns an isolated process to render HTML.
        Enforces a hard 5-second timeout.
        """
        if not PreviewGenerator._is_enabled():
            print("[STABILIZATION] Preview skipped: Feature disabled by default.")
            return [] if all_pages else None

        worker_script = PreviewGenerator._get_worker_path()
        
        # Create temporary files for communication
        # We use files because stdout can be unreliable for large binary data on Windows cmd
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.html")
            # [FIX] Force PNG extension
            output_file = os.path.join(tmpdir, "output.png")
            
            try:
                with open(input_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                # Command to run the worker
                # Use sys.executable to ensure we use the same environment
                # [FIX] Always use PNG for Preview. 
                # PDF cannot be displayed in QLabel. We rely on render_worker to handle height/pagination.
                target_format = "png"
                output_file = os.path.join(tmpdir, "output.png")
                
                cmd = [
                    sys.executable,
                    worker_script,
                    "--input", input_file,
                    "--output", output_file,
                    "--format", target_format
                ]
                
                logger.info(f"Spawning render worker for PREVIEW (timeout=5.0s, html_len={len(html_content)})")
                result = subprocess.run(
                    cmd,
                    timeout=5.0,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and os.path.exists(output_file):
                    with open(output_file, "rb") as f:
                        img_bytes = f.read()
                    
                    if all_pages:
                        return [img_bytes]
                    return img_bytes
                
                elif result.returncode == 5:
                     logger.error("Render failed: MISSING_GTK_DEPENDENCY")
                     raise RuntimeError("MISSING_DEPENDENCY")
                
                else:
                    err_msg = (result.stderr or result.stdout or "Unknown Error")[:2000]
                    logger.error(f"Render worker failed (Code {result.returncode}): {err_msg}")
            
            except subprocess.TimeoutExpired as te:
                if te.process:
                    te.process.kill()
                    te.process.wait()
                logger.error("Render worker TIMED OUT (5.0s limit reached).")
            except RuntimeError as re:
                 if str(re) == "MISSING_DEPENDENCY":
                      raise re
                 logger.error(f"Runtime error: {re}")
            except Exception as e:
                logger.error(f"Render manager error: {e}")
                
        return [] if all_pages else None

    @staticmethod
    def generate_pdf(html_content, output_path):
        """
        [ULTRA-SAFE] Renders HTML to PDF using isolated worker process.
        - Proper Timeout Capture: Kills process on hang.
        - Directory Guard: Ensures output path exists.
        - Cleanup: Deletes partial/corrupt files on failure.
        - Thread-Safe Logging: Uses logging module.
        """
        if not PreviewGenerator._is_enabled():
            return False, "FEATURE_DISABLED"

        worker_script = PreviewGenerator._get_worker_path()
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = os.path.join(tmpdir, "input.html")
            try:
                with open(input_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                cmd = [
                    sys.executable,
                    worker_script,
                    "--input", input_file,
                    "--output", output_path,
                    "--format", "pdf"
                ]
                
                logger.info(f"Spawning render worker for PDF (timeout=20.0s, html_len={len(html_content)})")
                
                result = subprocess.run(
                    cmd,
                    timeout=20.0,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info("PDF Generation successful.")
                    return True, "Success"
                
                elif result.returncode == 5:
                    logger.error("PDF Generation failed: MISSING_GTK_DEPENDENCY")
                    if os.path.exists(output_path): os.remove(output_path)
                    return False, "MISSING_DEPENDENCY"
                else:
                    err_msg = (result.stderr or result.stdout or "Unknown Error")[:2000]
                    logger.error(f"PDF worker failed (Code {result.returncode}): {err_msg}")
                    if os.path.exists(output_path): os.remove(output_path)
                    return False, err_msg

            except subprocess.TimeoutExpired as te:
                if te.process:
                    te.process.kill()
                    te.process.wait()
                logger.error("PDF worker TIMED OUT (20.0s limit reached).")
                if os.path.exists(output_path): os.remove(output_path)
                return False, "TIMEOUT"
            except Exception as e:
                logger.error(f"PDF generation error: {e}")
                if os.path.exists(output_path): os.remove(output_path)
                return False, str(e)

        return False, "UNKNOWN_ERROR"

    @staticmethod
    def get_qpixmap_from_bytes(img_bytes):
        """Convert raw bytes to QPixmap for UI display"""
        if not img_bytes:
            return None
        
        try:
            image = QImage()
            if image.loadFromData(img_bytes):
                return QPixmap.fromImage(image)
        except Exception as e:
            print(f"Error converting bytes to QPixmap: {e}")
            
        return None
