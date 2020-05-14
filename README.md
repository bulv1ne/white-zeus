# white-zeus

LoadBalancer:
- Listens to connections
- Manages connections to nodes
- Start/stop nodes
- Connects directly to node's docker containers
  - Writes last connection access
  - Writes amount of connections in use

Node:
- Waits for LB to start container
- Starts/stops docker containers
- Monitors CPU/memory for each container


Flow:
- Requests comes in


Version 0.X
- Servers
  - 1 LoadBalancer
  - 1..N Nodes
- Container properties
  - Max connection count
  - Max memory usage
- Container lifecycle
  - Creation
    - LoadBalancer requests new docker container to be run from any node
    - Node handles start/stop docker containers
  - Connection count
    - Container has max connection count
    - LB increases/decreases connection count
    - LoadBalancer connects to Docker Containers directly
  - Removal
    - Node marks containers for to be removed
    - LB won't make new connections to containers marked as to be removed
    - LB closes connections to container
    - Node removes container
- Node connects to LB
  - Commands:
    - Ping
      - Node responds always with Pong
    - Start docker container
    - Get docker container info
