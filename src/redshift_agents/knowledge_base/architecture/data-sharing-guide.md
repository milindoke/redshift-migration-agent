# Redshift Data Sharing Configuration Guide

## Overview

Redshift data sharing allows a producer namespace to share data with consumer namespaces without copying data. This is the foundation of the hub-and-spoke architecture pattern. 

## Prerequisites

- Producer and consumer must be in the same AWS account (for this migration tool)
- Both must be Redshift Serverless namespaces 
- Producer namespace must have the data loaded before creating datashares 

## Setup Steps

### 1. Create Datashare on Producer
```sql
CREATE DATASHARE migration_share;
```

### 2. Add Schema and Tables
```sql
ALTER DATASHARE migration_share ADD SCHEMA public;
ALTER DATASHARE migration_share ADD ALL TABLES IN SCHEMA public;
```

### 3. Grant Usage to Consumer Namespace
```sql
GRANT USAGE ON DATASHARE migration_share TO NAMESPACE '<consumer_namespace_id>';
```

### 4a. Create read-only Database from Datashare on Consumer
On the consumer workgroup:
```sql
CREATE DATABASE shared_db FROM DATASHARE migration_share OF NAMESPACE '<producer_namespace_id>';
```

or

### 4b. Create writable Database from Datashare on Consumer
On the consumer workgroup:
```sql
CREATE DATABASE shared_db WITH PERMISSIONS FROM DATASHARE migration_share OF NAMESPACE '<producer_namespace_id>';
```

If you create a database WITH PERMISSIONS, you can grant granular permissions on datashare objects to different users and roles. Without this, all users and roles granted USAGE permission on the datashare database are granted read permissions on all objects within the datashare database.

## Limitations

- Materialized views on shared data are supported but refresh runs on the consumer
- Stored procedures cannot directly reference shared database objects

## Rollback

To remove data sharing:
1. On consumer: `DROP DATABASE shared_db;`
2. On producer: `REVOKE USAGE ON DATASHARE migration_share FROM NAMESPACE '<consumer_namespace_id>';`
3. On producer: `DROP DATASHARE migration_share;`

## Datasharing considerations

- **Name datashares descriptively**: Use names like `analytics_share`, `reporting_share` to indicate purpose.

### General considerations for data sharing in Amazon Redshift

- **Default database**: When you read data from a datashare, you remain connected to your local cluster database. For more information about setting up and reading from a database created from a datashare, see Querying datashare objects and Materialized views on external data lake tables in Amazon Redshift Spectrum.

- **Connections**: You must be connected directly to a datashare database or run the USE command to write to datashares. You can also use three-part notation. The USE command is not supported on external tables.

- **Performance**: The performance of the queries on shared data depends on the compute capacity of the consumer clusters.

- **Data transfer charges**: Cross-Region data sharing includes additional cross-Region data-transfer charges. These data-transfer charges don't apply within the same Region, only across Regions. For more information, see Managing cost control for cross-Region data sharing. The consumer is charged for all compute and cross-region data transfer fees required to query the producer's data. The producer is charged for the underlying storage of data in their provisioned cluster or serverless namespace.

- **Data sharing within and between clusters**: You only need datashares when you are sharing data between different Amazon Redshift provisioned clusters or serverless workgroups. Within the same cluster, you can query another database using simple three-part notation database.schema.table as long as you have the required permissions on the objects in the other database.

- **Metadata Discovery**: When you're a consumer connected directly to a datashare database through the Redshift JDBC, ODBC, or Python drivers, you can view catalog data in the following ways: SQL SHOW commands. Querying information_schema tables and views. Querying SVV metadata views.

- **Permissions visibility**: Consumers can see the permissions granted to the datashares through the SHOW GRANTS SQL command.

- **Cluster encryption management for data sharing**: To share data across an AWS account, both the producer and consumer cluster must be encrypted. If both the producer and consumer clusters and serverless namespaces are in the same account, they must have the same encryption type (either both unencrypted, or both encrypted). In every other case, including Lake Formation managed datashares, both the consumer and producer must be encrypted. This is for security purposes. However, they don't need to share the same encryption key. To protect data in transit, all data is encrypted in transit through the encryption schema of the producer cluster. The consumer cluster adopts this encryption schema when data is loaded. The consumer cluster then operates as a normal encrypted cluster. Communications between the producer and consumer are also encrypted using a shared key schema. For more information about encryption in transit, Encryption in transit.

### Considerations for data sharing reads and writes in Amazon Redshift

- You can only share SQL UDFs through datashares. Python and Lambda UDFs aren't supported.

- If the producer database has specific collation, use the same collation settings for the consumer database.

- Amazon Redshift doesn't support nested SQL user-defined functions on producer clusters.

- Amazon Redshift doesn't support sharing tables with interleaved sort keys and views that refer to tables with interleaved sort keys.

- Amazon Redshift doesn't support accessing a datashare object which had a concurrent DDL occur between the Prepare and Execute of the access.

- Amazon Redshift doesn't support sharing stored procedures through datashares.

- Amazon Redshift doesn't support sharing metadata system views and system tables.

- **Compute type**: You must use Serverless workgroups, ra3.large clusters, ra3.xlplus clusters, ra3.4xl clusters, or ra3.16xl clusters to use this feature.

- **Isolation level**: Your database’s isolation level must be snapshot isolation in order to allow other Serverless workgroups and provisioned clusters to write to it.

- **Multi-statement queries and transactions**: Multi-statement queries outside of a transaction block aren't currently supported. As a result, if you are using a query editor like dbeaver and you have multiple write queries, you need to wrap your queries in an explicit BEGIN...END transaction statement. When multi-command statements are used outside of transactions, if the first command is a write to a producer database, subsequent write commands in the statement are only allowed to that producer database. If the first command is a read, subsequent write commands are only allowed to the used database, if set, otherwise to the local database. Note that the writes in a transaction are only supported to a single database.

- **Consumer sizing**: Consumer clusters must have at least 64 slices or more to perform writes using data sharing.

- **Views and materialized views**: You can't create, update, or alter views or materialized views on a datashare database.

- **Security**: You can't attach or remove security policies such as column-level (CLS), row-level (RLS) and dynamic data masking (DDM) to datashare objects.

- **Manageability**: Consumers warehouses can't add datashare objects or views referencing datashare objects to another datashare. Consumers also can't modify or drop an existing datashare.

- **Truncate operations**: Datashare writes support transactional truncates for remote tables. This is different than truncates that you run locally on a cluster, which are auto-commit. For more information about the SQL command, see TRUNCATE.

- **Cloning**: CREATE TABLE with LIKE clause statements support cloning from a single parent table when you write from consumer warehouses to producers.

---
*Source: https://docs.aws.amazon.com/redshift/latest/dg/datashare-considerations.html*