import io
import os
import subprocess
import tempfile
import sys
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from src.utils.config_manager import ConfigManager

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
            output_file = os.path.join(tmpdir, "output.png" if not all_pages else "output.pdf")
            
            try:
                with open(input_file, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                # Command to run the worker
                # Use sys.executable to ensure we use the same environment
                cmd = [
                    sys.executable,
                    worker_script,
                    "--input", input_file,
                    "--output", output_file,
                    "--format", "png" if not all_pages else "pdf"
                ]
                
                print(f"[STABILIZATION] Spawning render worker (timeout=5s)...")
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
                     # [STABILIZATION] Manifest Missing Dependency
                     print(f"[STABILIZATION] Render failed: Missing GTK3 Libraries.")
                     raise RuntimeError("MISSING_DEPENDENCY")
                
                else:
                    print(f"[STABILIZATION] Render worker failed (Code {result.returncode}): {result.stderr or result.stdout}")
            
            except subprocess.TimeoutExpired:
                print("[STABILIZATION] Render worker TIMED OUT (5s limit reached).")
            # Let RuntimeError propogate up to the UI if raised above
            except RuntimeError as re:
                 if str(re) == "MISSING_DEPENDENCY":
                      raise re
                 print(f"[STABILIZATION] Runtime error: {re}")
            except Exception as e:
                print(f"[STABILIZATION] Render manager error: {e}")
                
        return [] if all_pages else None

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
