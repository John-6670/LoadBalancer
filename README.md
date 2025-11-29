# HTTP Load Balancer

A Python-based HTTP Load Balancer implementation for a Computer Network practical assignment.

## Overview

This project implements a simple HTTP load balancer that distributes incoming HTTP requests across multiple backend servers. It supports two load balancing algorithms:

- **Round Robin (Weighted)**: Distributes requests across servers based on their assigned weights
- **Least Time**: Routes requests to the server with the lowest response time

## Project Structure

| File | Description |
|------|-------------|
| `http_server.py` | Defines the `SimpleHTTPServer` class - a configurable backend HTTP server with support for simulated errors and timeouts. Provides a `/healthz` endpoint for health checks. |
| `start_servers.py` | Server manager that starts 6 backend servers (ports 8080-8085) with various error/timeout configurations for testing. |
| `http_load_balancer.py` | The main load balancer program that routes incoming requests to backend servers based on the configured algorithm. |
| `test_load_balancer.py` | Test suite that validates the load balancer functionality including routing, algorithms, and error handling. |

## How to Run

### Prerequisites

- Python 3.x
- `requests` library (`pip install requests`)

### Step-by-Step Instructions

**Important**: The components must be started in the following order:

1. **Start the backend servers**
   ```bash
   python start_servers.py
   ```
   This starts 6 HTTP servers on ports 8080-8085.

2. **Start the load balancer** (in a new terminal)
   ```bash
   python http_load_balancer.py
   ```
   The load balancer runs on `localhost:8000` by default.

3. **Run the tests** (in a new terminal)
   ```bash
   python test_load_balancer.py
   ```
   This runs a comprehensive test suite to validate the load balancer.

## CLI Commands

The load balancer supports the following interactive commands:

| Command | Description |
|---------|-------------|
| `- list` | Lists all upstream servers and their health status, including request statistics and response times |
| `- quit` | Gracefully stops the load balancer |

## Configuration

### Upstream Server Groups

The load balancer is preconfigured with two domain groups:

| Domain | Algorithm | Servers (ports) |
|--------|-----------|-----------------|
| `round_robin.cn.edu` | Round Robin (Weighted) | 8080 (weight 1), 8081 (weight 3), 8082 (weight 2) |
| `least_time.cn.edu` | Least Time | 8083, 8084, 8085 |

### Backend Server Configuration

The `start_servers.py` script starts servers with the following configurations:

| Port | Error Rate | Timeout Rate |
|------|------------|--------------|
| 8080 | 0% | 0% |
| 8081 | 0% | 0% |
| 8082 | 10% | 20% |
| 8083 | 5% | 10% |
| 8084 | 0% | 30% |
| 8085 | 0% | 0% |

## Features

- **Health Monitoring**: Automatic health checks on backend servers via `/healthz` endpoint
- **Domain-based Routing**: Routes requests based on the `Host` header
- **Weighted Round Robin**: Distributes load according to server weights
- **Least Time Algorithm**: Routes to the fastest responding server
- **Error Handling**: Proper HTTP error responses (400, 404, 502, 503, 504)
- **Concurrent Request Handling**: Multi-threaded request processing