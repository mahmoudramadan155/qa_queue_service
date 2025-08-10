```bash
sudo su
```

or for a root shell with your environment variables intact:

```bash
sudo -i
```

Then run your Docker commands as root.

---

If you want to avoid typing `sudo` every time, add your user to the `docker` group:

```bash
sudo usermod -aG docker $USER
```

```bash
apt-get update && apt-get install -y curl
```

Once you run

```bash
docker-compose up -d
```

By default, Docker Compose does not start services under profiles: unless you specify them.
In your YAML, Elasticsearch and ChromaDB both have a profiles: section:

```bash
profiles:
  - elasticsearch

profiles:
  - chromadb

```

```bash
docker-compose --profile elasticsearch --profile chromadb up -d
```

you can test if **all services** are running and healthy with these steps:

---

### **1️⃣ Check container status**

```bash
docker ps
```

* You should see `postgres`, `qdrant`, `elasticsearch`, and `chromadb` containers **Up**.
* The `STATUS` column will say `healthy` if the healthchecks passed.

---

### **2️⃣ Check health status directly**

```bash
docker inspect --format='{{.Name}} {{.State.Health.Status}}' $(docker ps -q)
```

* This will print each container name with its health status (`healthy`, `starting`, `unhealthy`).

---

### **3️⃣ Test each service manually**

#### **PostgreSQL**

```bash
docker exec -it postgres_db psql -U qa_user -d qa_db -c '\l'
docker exec -it postgres_db psql -U qa_user -d qa_db
```


```bash
\dt          -- List all tables
SELECT * FROM your_table LIMIT 10;
```


```bash
docker exec -t postgres_db pg_dump -U qa_user qa_db > backup.sql
```

Expected: List of databases including `qa_db`.

---

#### **Qdrant**

List all collections:
```bash
curl -f http://localhost:6333/readyz
curl http://localhost:6333/collections
curl http://localhost:6333/collections/qa_documents
curl http://localhost:6333/metrics
```

Expected:

```json
{"status":"ok"}
```

Export (snapshot) a collection:

```bash
docker cp qdrant_db:/qdrant/storage ./qdrant_snapshots
```


---

#### **Elasticsearch** (only if running with `--profile elasticsearch`)

```bash
curl http://localhost:9200/_cluster/health?pretty
curl http://localhost:9200/_cat/indices?v
```

Expected: JSON with `"status": "green"` or `"yellow"`.

---

#### **ChromaDB** (only if running with `--profile chromadb`)

```bash
curl http://localhost:8001/api/v1/heartbeat
curl http://localhost:8001/api/v2/heartbeat

```

Expected: Response like `{"message": "Chroma is alive!"}` (depends on version).

---

### **4️⃣ View logs for any container**

If one is not healthy:

```bash
docker logs postgres
docker logs qdrant
docker logs elasticsearch
docker logs chromadb
```

---


# Qdrant Integration Guide

## Overview

Qdrant has been successfully integrated into your AI Question-Answering Service as a vector database option. Qdrant is a high-performance vector similarity search engine with excellent features for production use.

## Features of Qdrant Integration

- **High Performance**: Optimized for speed and memory efficiency
- **User Isolation**: Complete separation of user data using filters
- **Flexible Deployment**: Local storage or server mode
- **HNSW Algorithm**: Efficient approximate nearest neighbor search
- **Payload Filtering**: Advanced filtering capabilities
- **Horizontal Scaling**: Can be clustered for high availability

## Qdrant Web UI

Access Qdrant's web interface at http://localhost:6333/dashboard

Features:
- Collection management
- Vector search testing
- Performance metrics
- Collection statistics

## Performance Comparison

| Feature | ChromaDB | Elasticsearch | **Qdrant** |
|---------|----------|---------------|-------------|
| Speed | Good | Good | **Excellent** |
| Memory Usage | Medium | High | **Low** |
| Scalability | Limited | Good | **Excellent** |
| Setup Complexity | Easy | Medium | **Easy** |
| Production Ready | Good | Excellent | **Excellent** |


### Backup and Recovery
```bash
# Backup Qdrant data
docker run --rm -v qdrant_data:/source -v $(pwd)/backup:/backup alpine tar czf /backup/qdrant_backup.tar.gz -C /source .

# Restore Qdrant data
docker run --rm -v qdrant_data:/target -v $(pwd)/backup:/backup alpine tar xzf /backup/qdrant_backup.tar.gz -C /target
```

## Benefits of Using Qdrant

1. **Superior Performance**: Faster search and lower memory usage
2. **Production Ready**: Built for high-load production environments
3. **Easy Scaling**: Simple horizontal scaling capabilities
4. **Rich Filtering**: Advanced payload filtering for complex queries
5. **Active Development**: Regular updates and improvements
6. **Great Documentation**: Comprehensive guides and examples

