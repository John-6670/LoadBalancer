import socket
import threading
import time


ROUND_ROBIN = "round_robin"
LEAST_TIME = "least_time"
LOAD_BALANCING_ALGORITHMS = [ROUND_ROBIN, LEAST_TIME]


class HTTPLoadBalancer:
    def __init__(self, lb_host='localhost', lb_port=8000):
        """
        Initialize the HTTP load balancer
        """
        self.lb_host = lb_host
        self.lb_port = lb_port
        self.lb_socket = None
        self.running = False
        
        # Upstream servers configuration
        self.upstream_groups = {
            "round_robin.cn.edu": {
                "algorithm": ROUND_ROBIN,
                "servers": [
                    {"host": "127.0.0.1", "port": 8080, "weight": 1, "healthy": True, "timeout": 2},
                    {"host": "127.0.0.1", "port": 8081, "weight": 3, "healthy": True, "timeout": 2},
                    {"host": "domain.cn.edu", "port": 8082, "weight": 2, "healthy": True, "timeout": 3},
                ]
            },
            "least_time.cn.edu": {
                "algorithm": LEAST_TIME,
                "servers": [
                    {"host": "127.0.0.1", "port": 8083, "weight": 1, "healthy": True, "timeout": 2},
                    {"host": "127.0.0.1", "port": 8084, "weight": 1, "healthy": True, "timeout": 2},
                    {"host": "domain.cn.edu", "port": 8085, "weight": 1, "healthy": True, "timeout": 3},
                ]
            }
        }
        
        self.server_stats = {domain: {"total_requests": 0, "failed_requests": 0} for domain in self.upstream_groups}
        self._threads = []     
        
    def start_load_balancer(self):
        """
        Start the HTTP load balancer
        """
        try:
            self.lb_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.lb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.lb_socket.bind((self.lb_host, self.lb_port))
            self.lb_socket.listen(10)
            self.running = True
            
            print(f" HTTP Load Balancer started on {self.lb_host}:{self.lb_port}")
            for domain, group in self.upstream_groups.items():
                print(f" Domain: {domain}")
                print(f"  Algorithm: {group['algorithm']}")
                print(f"  Servers: {len(group['servers'])}")
            print("=" * 50)
            
            health_thread = threading.Thread(target=self.monitor_health, daemon=True, name="health")
            health_thread.start()
            self._threads.append(health_thread)

            # Accept HTTP connections
            command_thread = threading.Thread(target=self.handle_commands, daemon=True, name="command")
            command_thread.start()
            self._threads.append(command_thread)

            while self.running:
                try:
                    self.lb_socket.settimeout(1.0)  
                    client_socket, client_address = self.lb_socket.accept()
                    t = threading.Thread(
                        target=self.handle_http_request,
                        args=(client_socket, client_address),
                        daemon=True,
                        name=f"client-{client_address[0]}:{client_address[1]}"
                    )
                    t.start()
                    self._threads.append(t)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Load balancer error: {e}")
                        
        except Exception as e:
            print(f"Failed to start load balancer: {e}")
        finally:
            self.stop_load_balancer()
    
    def select_upstream_server(self, domain: str):
        """
        Select an upstream server using the configured algorithm for the specified domain

        :param domain: The domain name to select the upstream server from
        :return: The selected upstream server from upstream servers list
        """
        if domain not in self.upstream_groups:
            return None
        
        group = self.upstream_groups[domain]
        algorithm = group["algorithm"]
        servers = group["servers"]

        good_servers = [s for s in servers if s.get("healthy", True)]
        if not good_servers:
            return None

        # Route incoming requests to the appropriate upstream server group based on the Host header
        # Make sure to filter out unhealthy servers
        # Use the configured algorithm for the specified domain
        server = None
        if algorithm == ROUND_ROBIN:
            # TODO: Implement weights round robin algorithm
            if not hasattr(self, f'rr_counter'):
                setattr(self, f'rr_counter', 0)

            counter = getattr(self, f'rr_counter')
            total_weight = sum(s["weight"] for s in good_servers)

            # Select server based on weighted round-robin
            current_weight = 0
            for s in good_servers:
                current_weight += s["weight"]
                if counter % total_weight < current_weight:
                    server = s
                    break

            # Increment counter and wrap at total_weight
            counter = (counter + 1) % total_weight
            setattr(self, f'rr_counter', counter)
            
            
        elif algorithm == LEAST_TIME:
            # Initialize response_time for servers that don't have it
            for s in good_servers:
                if "response_time" not in s:
                    s["response_time"] = float('inf')

            # Select server with minimum response time
            server = min(good_servers, key=lambda s: s["response_time"])
        
        return server
        
    def handle_http_request(self, client_socket, client_address):
        """
        Handle HTTP request from client
        """
        try:
            # Receive HTTP request
            request_data = client_socket.recv(4096)
            if not request_data:
                return
            
            # Parse Host header to determine routing
            request_str = request_data.decode('utf-8')
            host_header = self.extract_host_header(request_str)

            if not host_header:
                self.send_error_response(client_socket, 400, "Bad Request: Missing Host header")
                return

            upstream_server = self.select_upstream_server(host_header)
            if upstream_server is None:
                if host_header in self.upstream_groups:
                    self.send_error_response(client_socket, 503, "No Healthy Upstream")
                else:
                    self.send_error_response(client_socket, 404, "Domain Not Found")
                return

            # If there is the Host header routing failed, requests should be responed
            # with a default response from the load balancer
            # If routing has succeeded, forward the request to the upstream server
            # If the upstream group has no healthy servers, the request should be responded
            # with a 503 status code with message "No Healthy Upstream"
            result = self.forward_http_request(client_socket, upstream_server, request_data)
            upstream = result["upstream_server"]
            if result:
                if result.get("success"):
                    upstream["response_time"] = result["response_time"]
                    upstream["healthy"] = True
                    if host_header in self.server_stats:
                        self.server_stats[host_header]["total_requests"] += 1
                else:
                    if host_header in self.server_stats:
                        self.server_stats[host_header]["failed_requests"] += 1
                    upstream["healthy"] = False

        except Exception as e:
            print(f"Error handling request from {client_address}: {e}")
            self.send_error_response(client_socket, 500, "Internal Server Error: " + str(e))
        finally:
            client_socket.close()
    
    def extract_host_header(self, request_str):
        """
        Extract Host header from HTTP request
        """
        host_header: str = ""
        lines = request_str.split("\r\n")
        for line in lines:
            if line.lower().startswith("host:"):
                host_header = line.split(":", 1)[1].strip().split(":")[0]
                break
        return host_header
    
    def forward_http_request(self, client_socket, upstream_server, request_data):
        """
        Forward HTTP request to upstream server
        Returns response data and timing information for student use

        :param client_socket: The socket object for the client
        :param upstream_server: The upstream server to forward the request to
        :param request_data: The request data to forward to the upstream server
        :return: A dictionary containing the success, response_time, response_data, server_id, and upstream_server
        """
        upstream_socket = None
        start_time = time.time()

        try:
            upstream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            upstream_socket.settimeout(upstream_server["timeout"])
            upstream_socket.connect((upstream_server["host"], upstream_server["port"]))
            
            upstream_socket.send(request_data)
            
            response_data = upstream_socket.recv(4096)
            client_socket.send(response_data)
            
            response_time = time.time() - start_time
            
            # Return data for student use (statistics, passive health check, etc.)
            return {
                "success": True,
                "response_time": response_time,
                "response_data": response_data,
                "server_id": f"{upstream_server['host']}:{upstream_server['port']}",
                "upstream_server": upstream_server
            }
            
        except socket.timeout:
            print(f"Timeout connecting to upstream {upstream_server['host']}:{upstream_server['port']}")
            self.send_error_response(client_socket, 504, "504 Gateway Timeout: " + str(e))
            return {
                "success": False,
                "error": "timeout",
                "server_id": f"{upstream_server['host']}:{upstream_server['port']}",
                "upstream_server": upstream_server
            }
        except Exception as e:
            print(f"Error connecting to upstream {upstream_server['host']}:{upstream_server['port']}: {e}")
            self.send_error_response(client_socket, 502, "502 Bad Gateway: " + str(e))
            return {
                "success": False,
                "error": str(e),
                "server_id": f"{upstream_server['host']}:{upstream_server['port']}",
                "upstream_server": upstream_server
            }
        finally:
            if upstream_socket:
                upstream_socket.close()
    
    def monitor_health(self):
        """
        Monitor upstream server health
        """
        while self.running:
            try:
                # Check the health of all upstream servers and update the health status
                for domain, group in self.upstream_groups.items():
                    for server in group["servers"]:

                        # Check health of each server
                        server["healthy"] = self.check_server_health(server)
            except Exception as e:
                print(f"Health monitoring error: {e}, Backing off for 5 seconds")
                time.sleep(5)
            finally:
                time.sleep(10)


    def check_server_health(self, server):
        """
        Check if a server is healthy by making a health check request
        """
        try:
            health_request = (
                "GET /healthz HTTP/1.1\r\n"
                f"Host: {server['host']}\r\n"
                "Connection: close\r\n"
                "\r\n"
            )
            
            health_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            health_socket.settimeout(server["timeout"])
            health_socket.connect((server["host"], server["port"]))
            health_socket.send(health_request.encode('utf-8'))
            
            response = health_socket.recv(1024).decode('utf-8')
            health_socket.close()
            
            health_check_result: bool = False

            if "200 OK" in response:
                health_check_result = True
            else:
                health_check_result = False
            return health_check_result
                
        except Exception as e:
            print(f"Health check failed for {server['host']}:{server['port']}: {e}")
            return False
    
    def handle_commands(self):
        """
        Handle load balancer commands
        """
        # LoadBalancer should support the following commands:
        # - list: list all upstream servers and their health status
        # - quit: stop the load balancer
        while self.running:
            try:
                cmd = input("lb> ")
            except (EOFError, KeyboardInterrupt):
                self.quit_load_balancer()
                break

            if not cmd:
                continue

            if cmd == "- quit":
                self.quit_load_balancer()
                break
            elif cmd == "- list":
                self.list_upstream_servers()
            else:
                print(f"Unknown command: {cmd}.")
        

    def list_upstream_servers(self):
        """
        List upstream servers and their health status
        """
        print("Upstream Servers Status:")
        print("=" * 40)
        for dom, grp in self.upstream_groups.items():
            algorithm = grp.get("algorithm", "?")
            stat = self.server_stats.get(dom, {"total_requests": 0, "failed_requests": 0})

            print("Domain:", dom)
            print("Algorithm:", algorithm)
            print(
                "  Requests: total={0} failed={1}".format(
                    stat["total_requests"], stat["failed_requests"]
                )
            )

            for i, srv in enumerate(grp["servers"], start=1):
            # Resolve health status (keeps same behavior)
                health_flag = srv.get("healthy", True)
                health_state = "Healthy" if health_flag else "Unhealthy"

            # Resolve response time display
                resp_t = srv.get("response_time")
                if isinstance(resp_t, (int, float)):
                    rt_str = "{:.4f}s".format(resp_t)
                else:
                    rt_str = "n/a"

                print(
                    "    [{}] {}:{} weight={} timeout={} status={} last_rt={}".format(
                        i,
                        srv["host"],
                        srv["port"],
                        srv.get("weight", 1),
                        srv.get("timeout", "?"),
                        health_state,
                        rt_str,
                    )
                )
            print()

    def quit_load_balancer(self):
        """
        Quit the load balancer
        """
        self.running = False
        if self.lb_socket:
            try:
                self.lb_socket.close()
            except Exception:
                pass
        print("Shutting down load balancer...")
    
    def send_error_response(self, client_socket, status: int, message: str = ""):
        """Send HTTP error response to client"""
        http_response = ( 
            f"HTTP/1.1 {status} {message}\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(message)}\r\n"
            "Connection: close\r\n"
            "\r\n"
            f"{message}"
        )
        client_socket.send(http_response.encode('utf-8'))
    
    def stop_load_balancer(self):
        """Stop the load balancer"""
        self.running = False
        if self.lb_socket:
            self.lb_socket.close()
        print("Load balancer stopped")

def main():
    """
    Main function to start the HTTP load balancer
    """
    print("HTTP LOAD BALANCER")
    print("=" * 60)

    lb = HTTPLoadBalancer()
    try:
        lb.start_load_balancer()
    except KeyboardInterrupt:
        print("\nLoad balancer stopped by user")
    finally:
        lb.stop_load_balancer()

if __name__ == "__main__":
    main()
