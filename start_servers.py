import sys
import time
import threading
import signal


class ServerManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def start_server(self, port, error_rate, timeout_rate, timeout_duration, server_id):
        try:
            print(f"Starting HTTP Server {server_id} on port {port} (error rate: {error_rate*100}%, timeout rate: {timeout_rate*100}%)")
            
            from http_server import SimpleHTTPServer
            server = SimpleHTTPServer(host='0.0.0.0', port=port, error_rate=error_rate, timeout_rate=timeout_rate, timeout_duration=timeout_duration)
            server.start_server()
            
        except Exception as e:
            print(f"Error starting server {server_id}: {e}")
    
    def start_all_servers(self):
        servers = [
            (8080, 0.0, 0.0, 5, 0),   # 0% error rate, 0% timeout rate
            (8081, 0.0, 0.0, 5, 1),   # 0% error rate, 0% timeout rate
            (8082, 0.1, 0.2, 5, 2),   # 10% error rate, 20% timeout rate
            (8083, 0.05, 0.1, 5, 3),  # 5% error rate, 10% timeout rate
            (8084, 0.0, 0.3, 5, 4),   # 0% error rate, 30% timeout rate
            (8085, 0.0, 0.0, 5, 5),   # 0% error rate, 0% timeout rate
        ]
        
        for port, error_rate, timeout_rate, timeout_duration, server_id in servers:
            server_thread = threading.Thread(
                target=self.start_server,
                args=(port, error_rate, timeout_rate, timeout_duration, server_id),
                daemon=True
            )
            server_thread.start()
            time.sleep(1)
        
        print("All HTTP servers started!")
        print("You can now start the load balancer")
        print("=" * 50)
    
    def signal_handler(self, signum, frame):
        print("\nShutting down servers...")
        self.running = False
        sys.exit(0)

def main():
    print("=" * 60)
    print("HTTP SERVER MANAGER - LOAD BALANCER SETUP")
    print("=" * 60)
    print("This script starts multiple HTTP servers for load balancer testing")
    print("=" * 60)
    
    manager = ServerManager()
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    try:
        manager.start_all_servers()
        
        while manager.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nServer manager stopped by user")
    except Exception as e:
        print(f"Server manager error: {e}")

if __name__ == "__main__":
    main()
