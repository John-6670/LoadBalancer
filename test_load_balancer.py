import socket
import time
import threading
import requests


class LoadBalancerTester:
    def __init__(self, lb_host='localhost', lb_port=8000):
        self.lb_host = lb_host
        self.lb_port = lb_port
        self.test_results = []
        
    def test_basic_http_request(self):
        try:
            print("=" * 50)
            print("Testing basic HTTP request...")
            
            response = requests.get(f"http://{self.lb_host}:{self.lb_port}/", timeout=10, headers={'Host': 'round_robin.cn.edu'})
            
            if response.status_code == 200:
                print("✅ Basic HTTP request successful")
                print(f"  Response:{response.text[:100]}...")
                return True
            else:
                print(f"❌ HTTP request failed with status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Basic HTTP test failed: {e}")
            return False
    
    def test_domain_routing(self):
        try:
            print("=" * 50)
            print("Testing domain-based routing...")
            
            test_domains = [
                "round_robin.cn.edu",
                "least_time.cn.edu",
                "unknown.domain.com"
            ]
            
            results = []
            
            for domain in test_domains:
                try:
                    headers = {'Host': domain}
                    response = requests.get(f"http://{self.lb_host}:{self.lb_port}/", 
                                          headers=headers, timeout=5)
                    
                    print(f"  Domain: {domain} -> Status: {response.status_code}")
                    results.append((domain, response.status_code))
                    
                except Exception as e:
                    print(f"  Domain: {domain} -> Error: {e}")
                    results.append((domain, "error"))

                if domain == "round_robin.cn.edu":
                    if response.status_code != 200:
                        return False
                elif domain == "least_time.cn.edu":
                    if response.status_code != 200:
                        return False
                else:
                    if response.status_code != 404:
                        return False

            return True
            
        except Exception as e:
            print(f"❌ Domain routing test failed: {e}")
            return False
    
    def test_host_header_parsing(self):
        try:
            print("=" * 50)
            print("🧪 Testing Host header parsing...")
            
            test_cases = [
                {
                    "name": "Standard Host Header",
                    "request": "GET / HTTP/1.1\r\nHost: round_robin.cn.edu\r\nConnection: close\r\n\r\n"
                },
                {
                    "name": "Host Header with Port",
                    "request": "GET / HTTP/1.1\r\nHost: round_robin.cn.edu:8000\r\nConnection: close\r\n\r\n"
                },
                {
                    "name": "Host Header with Spaces",
                    "request": "GET / HTTP/1.1\r\nHost:  round_robin.cn.edu  \r\nConnection: close\r\n\r\n"
                },
                {
                    "name": "Case Insensitive Host",
                    "request": "GET / HTTP/1.1\r\nHOST: round_robin.cn.edu\r\nConnection: close\r\n\r\n"
                },
                {
                    "name": "Multiple Host Headers",
                    "request": "GET / HTTP/1.1\r\nHost: round_robin.cn.edu\r\nHost: least_time.cn.edu\r\nConnection: close\r\n\r\n"
                }
            ]
            
            results = []
            
            for test_case in test_cases:
                print(f"\n📋 Testing: {test_case['name']}")
                
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((self.lb_host, self.lb_port))
                    client_socket.send(test_case['request'].encode('utf-8'))
            
                    response = client_socket.recv(4096).decode('utf-8')
                    client_socket.close()
                    
                    if "200 OK" in response:
                        print("Request successful")
                        results.append(True)
                    else:
                        print(f"Request failed: {response.split('\\n')[0]}")
                        results.append(False)
                                
                except Exception as e:
                    print(f"  ❌ Test failed: {e}")
                    results.append(False)
                
                time.sleep(0.5)
            
            success_count = sum(results)
            print(f"\n✅ Host header parsing test completed: {success_count}/{len(test_cases)} successful")
            
            return success_count > 0
                
        except Exception as e:
            print(f"❌ Host header parsing test failed: {e}")
            return False
    
    def test_round_robin_algorithm(self, num_requests=20):
        try:
            print("=" * 50)
            print(f"Testing Round Robin algorithm with {num_requests} requests...")
            
            server_responses = {}
            
            def send_request(request_id):
                try:
                    headers = {'Host': 'round_robin.cn.edu'}
                    response = requests.get(f"http://{self.lb_host}:{self.lb_port}/", 
                                          headers=headers, timeout=5)
                    
                    server_info = response.headers.get('X-Server-ID', 'unknown')
                    server_responses[request_id] = server_info
                    
                except Exception as e:
                    server_responses[request_id] = f"error: {e}"
            
            threads = []
            for i in range(num_requests):
                thread = threading.Thread(target=send_request, args=(i,))
                threads.append(thread)
                thread.start()
                time.sleep(0.1)
            
            for thread in threads:
                thread.join()
            
            server_counts = {}
            for server in server_responses.values():
                server_counts[server] = server_counts.get(server, 0) + 1
            
            print(f"✅ Round Robin distribution:")
            for server, count in server_counts.items():
                print(f"   Server {server}: {count} requests")
            
            return len(server_counts) > 1
            
        except Exception as e:
            print(f"❌ Round Robin test failed: {e}")
            return False
    
    def test_least_time_algorithm(self, num_requests=20):
        try:
            print("=" * 50)
            print(f"Testing Least Time algorithm with {num_requests} requests...")
            
            response_times = []
            server_selections = []
            
            def send_request(request_id):
                try:
                    headers = {'Host': 'least_time.cn.edu'}
                    start_time = time.time()
                    response = requests.get(f"http://{self.lb_host}:{self.lb_port}/", 
                                          headers=headers, timeout=5)
                    end_time = time.time()
                    
                    response_times.append(end_time - start_time)
                    server_info = response.headers.get('X-Server-ID', 'unknown')
                    server_selections.append(server_info)
                    
                except Exception as e:
                    response_times.append(float('inf'))
                    server_selections.append(f"error: {e}")
            
            threads = []
            for i in range(num_requests):
                thread = threading.Thread(target=send_request, args=(i,))
                threads.append(thread)
                thread.start()
                time.sleep(0.1)
            
            for thread in threads:
                thread.join()
            
            server_counts = {}
            for server in server_selections:
                server_counts[server] = server_counts.get(server, 0) + 1
            
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            print(f"✅ Least Time algorithm test completed:")
            print(f"   Average response time: {avg_response_time:.3f}s")
            for server, count in server_counts.items():
                print(f"   Server {server}: {count} requests")
            
            return len(server_counts) > 0
            
        except Exception as e:
            print(f"❌ Least Time test failed: {e}")
            return False
    
    def test_error_handling(self):
        try:
            print("=" * 50)
            print("Testing error handling...")
            
            try:
                headers = {'Host': 'unknown.domain.com'}
                response = requests.get(f"http://{self.lb_host}:{self.lb_port}/", 
                                      headers=headers, timeout=5)
                print(f"  Unknown domain: {response.status_code}")
            except Exception as e:
                print(f"  Unknown domain: Error - {e}")
            
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((self.lb_host, self.lb_port))
                client_socket.send(b"INVALID HTTP REQUEST\r\n\r\n")
                response = client_socket.recv(1024).decode('utf-8')
                client_socket.close()
                print(f"  Malformed request: {response.split('\\n')[0]}")
            except Exception as e:
                print(f"  Malformed request: Error - {e}")
            
            print("✅ Error handling test completed")
            return True
            
        except Exception as e:
            print(f"❌ Error handling test failed: {e}")
            return False
    
    def test_concurrent_routing(self, num_requests=20):
        try:
            print("=" * 50)
            print(f"Testing concurrent routing with {num_requests} requests...")
            
            responses = []
            threads = []
            
            def send_request(request_id):
                try:
                    domain = "round_robin.cn.edu" if request_id % 2 == 0 else "least_time.cn.edu"
                    headers = {'Host': domain}
                    response = requests.get(f"http://{self.lb_host}:{self.lb_port}/", 
                                          headers=headers, timeout=5)
                    
                    responses.append({
                        "id": request_id,
                        "domain": domain,
                        "status": response.status_code,
                        "server": response.headers.get('X-Server-ID', 'unknown')
                    })
                    
                except Exception as e:
                    responses.append({
                        "id": request_id,
                        "domain": "error",
                        "status": "error",
                        "server": str(e)
                    })
            
            for i in range(num_requests):
                thread = threading.Thread(target=send_request, args=(i,))
                threads.append(thread)
                thread.start()
                time.sleep(0.05)
            
            for thread in threads:
                thread.join()
            
            successful_requests = [r for r in responses if r["status"] == 200]
            failed_requests = [r for r in responses if r["status"] != 200]
            
            domain_counts = {}
            for response in successful_requests:
                domain = response["domain"]
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            print(f"✅ Concurrent routing test completed")
            print(f"   Successful requests: {len(successful_requests)}")
            print(f"   Failed requests: {len(failed_requests)}")
            print(f"   Domain distribution:")
            for domain, count in domain_counts.items():
                print(f"      {domain}: {count} requests")
            
            return len(successful_requests) > 0
            
        except Exception as e:
            print(f"❌ Concurrent routing test failed: {e}")
            return False
    
    def test_load_distribution(self, num_requests=50):
        try:
            print("=" * 50)
            print(f"Testing load distribution with {num_requests} requests...")
            
            responses = []
            threads = []
            
            def send_request(request_id):
                try:
                    domain = "round_robin.cn.edu" if request_id % 2 == 0 else "least_time.cn.edu"
                    headers = {'Host': domain}
                    response = requests.get(f"http://{self.lb_host}:{self.lb_port}/", 
                                          headers=headers, timeout=5)
                    responses.append({
                        "id": request_id,
                        "domain": domain,
                        "status": response.status_code,
                        "text": response.text[:50] if response.text else ""
                    })
                except Exception as e:
                    responses.append({
                        "id": request_id,
                        "domain": "error",
                        "status": "error",
                        "text": str(e)
                    })
            
            for i in range(num_requests):
                thread = threading.Thread(target=send_request, args=(i,))
                threads.append(thread)
                thread.start()
                time.sleep(0.05)

            for thread in threads:
                thread.join()
            
            successful_requests = [r for r in responses if r["status"] == 200]
            failed_requests = [r for r in responses if r["status"] != 200]
            
            domain_counts = {}
            for response in successful_requests:
                domain = response["domain"]
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            
            print(f"✅ Load distribution test completed")
            print(f"   Successful requests: {len(successful_requests)}")
            print(f"   Failed requests: {len(failed_requests)}")
            print(f"   Domain distribution:")
            for domain, count in domain_counts.items():
                print(f"      {domain}: {count} requests")
            
            return len(successful_requests) > 0
            
        except Exception as e:
            print(f"❌ Load distribution test failed: {e}")
            return False
    
    def run_comprehensive_test(self):
        print("=" * 60)
        
        test_results = []
        
        test_results.append(("Basic HTTP Request", self.test_basic_http_request()))
        test_results.append(("Domain Routing", self.test_domain_routing()))
        test_results.append(("Host Header Parsing", self.test_host_header_parsing()))
        test_results.append(("Round Robin Algorithm", self.test_round_robin_algorithm()))
        test_results.append(("Least Time Algorithm", self.test_least_time_algorithm()))
        test_results.append(("Error Handling", self.test_error_handling()))
        test_results.append(("Concurrent Routing", self.test_concurrent_routing()))
        test_results.append(("Load Distribution", self.test_load_distribution()))
        
        print("\n" + "=" * 60)
        print("TEST RESULTS:")
        print()

        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        print("=" * 60)
        
        return all(result for _, result in test_results)


def main():
    print ("======== HTTP LOAD BALANCER TESTER ========")

    tester = LoadBalancerTester()
    
    try:
        success = tester.run_comprehensive_test()
        
        if success:
            print("🎉 All automated tests passed!")
        else:
            print("⚠️  Some tests failed. Check the output above.")
        
    except KeyboardInterrupt:
        print("\n🛑 Testing stopped by user")
    except Exception as e:
        print(f"❌ Testing error: {e}")


if __name__ == "__main__":
    main()