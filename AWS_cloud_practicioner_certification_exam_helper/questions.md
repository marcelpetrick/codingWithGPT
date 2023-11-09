### Set 4:

1. **AWS Elastic Compute Cloud (EC2) Types:**
   Which EC2 instance type is optimized for compute-intensive workloads?
   - A. T2 instances
   - B. M5 instances
   - C. C5 instances
   - D. R5 instances
   > **Answer: C**
   > **Explanation:** C5 instances are optimized for compute-intensive workloads and offer a high compute-to-memory ratio, making them ideal for high-performance web servers, scientific modeling, batch processing, and distributed analytics.

2. **IAM Policies:**
   Which IAM feature allows you to set fine-grained access control to AWS resources?
   - A. IAM Roles
   - B. IAM Users
   - C. IAM Groups
   - D. IAM Policies
   > **Answer: D**
   > **Explanation:** IAM Policies are JSON documents that define permissions and can be attached to IAM users, groups, and roles to grant or deny access to AWS resources with fine-grained control.

3. **Amazon S3 Storage Classes:**
   For infrequently accessed data that requires long-term storage with rapid access when needed, which S3 storage class should you use?
   - A. S3 Standard-Infrequent Access (S3 Standard-IA)
   - B. S3 One Zone-Infrequent Access
   - C. S3 Glacier
   - D. S3 Intelligent-Tiering
   > **Answer: A**
   > **Explanation:** S3 Standard-IA is designed for data that is accessed less frequently, but requires rapid access when needed. It offers the durability, high throughput, and low latency of S3 Standard, but with a lower storage price.

4. **AWS Billing and Pricing:**
   What service or feature allows AWS customers to receive a bill that provides cost and usage information by different dimensions, such as by service or by tags?
   - A. AWS Budgets
   - B. AWS Cost and Usage Report
   - C. AWS Cost Explorer
   - D. Consolidated Billing
   > **Answer: B**
   > **Explanation:** The AWS Cost and Usage Report contains the most comprehensive set of AWS cost and usage data available, including additional metadata about AWS services, pricing, and reservations (e.g., Amazon EC2 Reserved Instances).

5. **Auto Scaling:**
   What is the main purpose of AWS Auto Scaling?
   - A. To automatically update your EC2 instances
   - B. To adjust the number of active EC2 instances in response to load
   - C. To scale the storage capacity of EBS volumes
   - D. To change the instance types of running instances based on demand
   > **Answer: B**
   > **Explanation:** AWS Auto Scaling monitors your applications and automatically adjusts capacity to maintain steady, predictable performance at the lowest possible cost.

6. **AWS Global Infrastructure:**
   Which component of AWS Global Infrastructure does Amazon CloudFront use to deliver content to users with lower latency?
   - A. Availability Zones
   - B. Data Centers
   - C. Edge Locations
   - D. Regional Edge Caches
   > **Answer: C**
   > **Explanation:** Amazon CloudFront is a content delivery network (CDN) service that delivers data, videos, applications, and APIs to customers globally with low latency, high transfer speeds, all within a developer-friendly environment. It uses a global network of edge locations to cache content closer to users.

7. **Amazon Database Services:**
   Which AWS service is a fully managed petabyte-scale data warehouse service in the cloud?
   - A. Amazon RDS
   - B. Amazon DynamoDB
   - C. Amazon Redshift
   - D. Amazon ElastiCache
   > **Answer: C**
   > **Explanation:** Amazon Redshift is a fast, fully managed, petabyte-scale data warehouse that makes it simple and cost-effective to analyze all your data using standard SQL and your existing Business Intelligence (BI) tools.

8. **AWS Management Tools:**
   Which AWS service provides a unified user interface that simplifies the management of your AWS resources?
   - A. AWS Management Console
   - B. AWS Command Line Interface (CLI)
   - C. AWS SDKs
   - D. AWS APIs
   > **Answer: A**
   > **Explanation:** The AWS Management Console is a web-based interface that provides an easy-to-use, graphical representation of your AWS resources and simplifies the process of creating, configuring, and managing AWS services.

9. **Security Groups vs. Network Access Control Lists (NACLs):**
   What is the difference between security groups and network access control lists (NACLs) in Amazon VPC?
   - A. Security groups are stateful; NACLs are stateless.
   - B. Security groups are for outbound traffic; NACLs are for inbound traffic.
   - C. Security groups are resource-based; NACLs are account-based.
   - D. Security groups are optional; NACLs are mandatory.
   > **Answer: A**
   > **Explanation:** In Amazon VPC, security groups are stateful (return traffic is automatically allowed, regardless of any rules), while network access control lists (NACLs) are stateless (return traffic must be explicitly allowed by rules).

10. **AWS Support Plans:**
    Which AWS Support plan provides a full set of AWS Trusted Advisor checks and guidance to provision your resources following best practices to help reduce costs, increase performance and fault tolerance, and improve security?
    - A. Basic
    - B. Developer
    - C. Business
    - D. Enterprise
    > **Answer: D**
    > **Explanation:** The Enterprise Support plan provides access to all AWS Trusted Advisor checks. It is the most comprehensive and costly plan, designed for businesses with substantial use of AWS.


### Set 5:

1. **AWS Service for Serverless Backend:**
   Which AWS service is designed to let you run code without provisioning or managing servers and scales automatically?
   - A. Amazon EC2
   - B. AWS Elastic Beanstalk
   - C. AWS Lambda
   - D. Amazon Lightsail
   > **Answer: C**
   > **Explanation:** AWS Lambda is a serverless compute service that runs your code in response to events and automatically manages the underlying compute resources for you.

2. **Amazon RDS Feature:**
   What feature of Amazon RDS helps you to failover to a standby replica in another Availability Zone in case of an outage?
   - A. Multi-AZ Deployments
   - B. Read Replicas
   - C. Elastic IP Addresses
   - D. Automated Backups
   > **Answer: A**
   > **Explanation:** Multi-AZ Deployments for Amazon RDS provide enhanced availability and durability for Database (DB) Instances, making them a natural fit for production database workloads. When you provision a Multi-AZ DB Instance, Amazon RDS automatically creates a primary DB instance and synchronously replicates the data to a standby instance in a different Availability Zone (AZ).

3. **Identifying AWS Cost Drivers:**
   What AWS tool can you use to identify which AWS services are driving your costs?
   - A. AWS Cost and Usage Report
   - B. AWS Budgets
   - C. AWS Price List API
   - D. AWS Total Cost of Ownership (TCO) Calculator
   > **Answer: A**
   > **Explanation:** The AWS Cost and Usage Report tracks your AWS usage and provides estimated charges associated with your account. It breaks down your costs by service to help identify where you are spending money.

4. **AWS Support Plan Feature:**
   Which feature is available to all AWS customers regardless of the support plan they are subscribed to?
   - A. 24/7 customer service
   - B. Access to AWS Trusted Advisor
   - C. Infrastructure Event Management
   - D. AWS Personal Health Dashboard
   > **Answer: D**
   > **Explanation:** The AWS Personal Health Dashboard provides alerts and remediation guidance when AWS is experiencing events that may impact you. It is available to all AWS customers.

5. **Amazon EC2 Reserved Instances:**
   How do Reserved Instances (RIs) provide savings over On-Demand pricing in Amazon EC2?
   - A. RIs provide a discount for upfront payment and a commitment for a term of one or three years.
   - B. RIs charge you only when you use them.
   - C. RIs offer a discount because they utilize unused EC2 capacity.
   - D. RIs are free of charge for internal AWS use.
   > **Answer: A**
   > **Explanation:** Reserved Instances provide a significant discount compared to On-Demand pricing and are best for use cases with steady state usage. Customers pay for the entire term (one or three years), regardless of how they use it.

6. **AWS Edge Services:**
   Which AWS service is primarily used to deliver content with low latency and high data transfer speeds to end-users?
   - A. Amazon S3
   - B. Amazon EBS
   - C. Amazon CloudFront
   - D. AWS Direct Connect
   > **Answer: C**
   > **Explanation:** Amazon CloudFront is a fast content delivery network (CDN) service that securely delivers data, videos, applications, and APIs to customers globally with low latency and high transfer speeds.

7. **IAM Security Best Practice:**
   What is a recommended security best practice when managing AWS IAM policies?
   - A. Share IAM user credentials among team members to simplify management.
   - B. Grant all IAM users administrative permissions to ensure access to resources.
   - C. Apply the principle of least privilege by granting only the permissions necessary.
   - D. Regularly rotate IAM user access keys every 5 years.
   > **Answer: C**
   > **Explanation:** A key security best practice when using IAM is to apply the principle of least privilege, which means granting only the permissions required to perform a task.

8. **Scaling Databases in AWS:**
   How can you scale a relational database in AWS when you need higher performance?
   - A. Use an Amazon S3 bucket to offload static content.
   - B. Upgrade to a larger EC2 instance type for your database.
   - C. Split your database into multiple smaller, distributed databases.
   - D. Add Read Replicas in Amazon RDS.
   > **Answer: D**
   > **Explanation:** To scale read performance, you can use Amazon RDS Read Replicas, which allow you to create one or more read-only copies of your database instance. This can increase performance by splitting read and write traffic.

9. **Amazon S3 Data Consistency Model:**
   As of December 2020, what type of consistency does Amazon S3 provide after a successful write of a new object?
   - A. Eventual Consistency
   - B. Strong Consistency
   - C. Read-after-write Consistency
   - D. Consistent Prefix Consistency
   > **Answer: B**
   > **Explanation:** Amazon S3 offers strong consistency automatically for all types of operations, which means that after a successful write of a new object or an overwrite of an existing object, any subsequent read request immediately receives the latest version of the object.

10. **AWS Cost Management:**
    What is a benefit of using AWS Organizations to manage multiple AWS accounts?
    - A. Shared compute resources between accounts
    - B. Centralized billing and consolidated cost reports
    - C. Automatic discounts on all AWS services
    - D. Unified networking by default between accounts
    > **Answer: B**
    > **Explanation:** AWS Organizations allows you to consolidate billing across multiple AWS accounts, enabling centralized tracking of charges and detailed cost reports.
