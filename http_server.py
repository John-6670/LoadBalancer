import socket
import threading
import time
import random
from datetime import datetime


class SimpleHTTPServer:
    def __init__(self, host='localhost', port=8080, error_rate=0.0, timeout_rate=0.0, timeout_duration=10):
        self.host = host
        self.port = port
        self.error_rate = error_rate
        self.timeout_rate = timeout_rate
        self.timeout_duration = timeout_duration
        self.server_socket = None
        self.running = False
        
    def start_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print(f"HTTP Server started on {self.host}:{self.port}")
            print(f"Error rate: {self.error_rate * 100}%")
            print(f"Timeout rate: {self.timeout_rate * 100}%")
            print(f"Timeout duration: {self.timeout_duration}s")
            print("=" * 50)
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        print(f"Server error: {e}")
                        
        except Exception as e:
            print(f"Failed to start server: {e}")
        finally:
            self.stop_server()
    
    def handle_client(self, client_socket, client_address):
        try:
            request = client_socket.recv(1024).decode('utf-8')
            
            request_line = request.split('\n')[0]
            method, path, version = request_line.split()
            
            print(f"{client_address[0]}:{client_address[1]} - {method} {path}")
            
            if path == '/healthz':
                response = self.handle_health_check()
            elif path == '/':
                response = self.handle_root()
            else:
                response = self.handle_404()
            
            client_socket.send(response.encode('utf-8'))
            
        except Exception as e:
            print(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
    
    def handle_health_check(self):
        if random.random() < self.timeout_rate:
            print(f"Health check timeout simulation (sleeping {self.timeout_duration}s)")
            time.sleep(self.timeout_duration)
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 2\r\n"
                f"X-Server-ID: {self.port}\r\n"
                "\r\n"
                "OK"
            )
            print("Health check passed after timeout (200)")
            return response
        
        if random.random() < self.error_rate:
            response = (
                "HTTP/1.1 502 Bad Gateway\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 13\r\n"
                f"X-Server-ID: {self.port}\r\n"
                "\r\n"
                "Service Unavailable"
            )
            print("Health check failed (502)")
        else:
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 2\r\n"
                f"X-Server-ID: {self.port}\r\n"
                "\r\n"
                "OK"
            )
            print("Health check passed (200)")
        
        return response
    
    def handle_root(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"Hello from HTTP Server!\nTimestamp: {timestamp}\nPort: {self.port}"
        
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"X-Server-ID: {self.port}\r\n"
            "\r\n"
            f"{body}"
        )
        return response
    
    def handle_404(self):
        response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/plain\r\n"
            "Content-Length: 13\r\n"
            f"X-Server-ID: {self.port}\r\n"
            "\r\n"
            "Not Found"
        )
        return response
    
    def set_error_rate(self, error_rate):
        self.error_rate = max(0.0, min(1.0, error_rate))
        print(f"Error rate set to {self.error_rate * 100}%")
    
    def set_timeout_rate(self, timeout_rate):
        self.timeout_rate = max(0.0, min(1.0, timeout_rate))
        print(f"Timeout rate set to {self.timeout_rate * 100}%")
    
    def set_timeout_duration(self, timeout_duration):
        self.timeout_duration = max(1.0, timeout_duration)
        print(f"Timeout duration set to {self.timeout_duration}s")
    
    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("HTTP Server stopped")

def main():
    print("=" * 50)
    print("SIMPLE HTTP SERVER")
    print("=" * 50)
    print("This server provides a /healthz endpoint for load balancer testing")
    print("=" * 50)
    
    server = SimpleHTTPServer(port=8080, error_rate=0.1, timeout_rate=0.2, timeout_duration=8)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    finally:
        server.stop_server()

if __name__ == "__main__":
    main()
