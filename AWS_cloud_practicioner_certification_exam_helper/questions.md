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

### Set 6:

1. **AWS Object Storage:**
   Which AWS service is an object storage service that offers scalability, data availability, security, and performance?
   - A. Amazon EBS
   - B. Amazon EFS
   - C. Amazon S3
   - D. Amazon Glacier
   > **Answer: C**
   > **Explanation:** Amazon S3 (Simple Storage Service) is an object storage service that offers industry-leading scalability, data availability, security, and performance.

2. **Amazon EC2 Purchasing Options:**
   Which EC2 purchasing option allows you to use the unused EC2 capacity at a significantly reduced rate?
   - A. Reserved Instances
   - B. On-Demand Instances
   - C. Spot Instances
   - D. Dedicated Hosts
   > **Answer: C**
   > **Explanation:** Spot Instances allow customers to purchase unused EC2 capacity at a reduced rate. However, these instances can be terminated by AWS with a two-minute notification when AWS needs the capacity back.

3. **AWS Compliance Programs:**
   What AWS service helps you automate compliance checks for the IT environment against industry standards and best practices?
   - A. AWS Config
   - B. AWS Identity and Access Management (IAM)
   - C. AWS Shield
   - D. AWS Inspector
   > **Answer: A**
   > **Explanation:** AWS Config is a service that enables you to assess, audit, and evaluate the configurations of your AWS resources. It helps with compliance auditing, security analysis, resource change tracking, and troubleshooting.

4. **Serverless Application Repository:**
   What is the purpose of the AWS Serverless Application Repository?
   - A. To manage server configurations for applications
   - B. To store and share serverless applications
   - C. To provide a version control system for Lambda functions
   - D. To deploy virtual servers on demand
   > **Answer: B**
   > **Explanation:** The AWS Serverless Application Repository is designed to enable teams, organizations, and individual developers to store and share reusable applications, and easily assemble and deploy serverless architectures in powerful new ways.

5. **Amazon VPC:**
   In Amazon VPC, what is the term for a virtual network dedicated to your AWS account?
   - A. Virtual Private Network (VPN)
   - B. Virtual Private Cloud (VPC)
   - C. Subnet
   - D. Internet Gateway
   > **Answer: B**
   > **Explanation:** A Virtual Private Cloud (VPC) is a virtual network dedicated to your AWS account. It is logically isolated from other virtual networks in the AWS Cloud.

6. **AWS Data Transfer Charges:**
   When does AWS NOT charge for data transfer?
   - A. Data transfer between different AWS services within the same region
   - B. Data transfer from an EC2 instance to the Internet
   - C. Data transfer into AWS from the Internet
   - D. Data transfer between EC2 instances and Amazon S3 in the same region
   > **Answer: C**
   > **Explanation:** AWS does not charge for all inbound data transfer (from the Internet to AWS). However, outbound data transfer and data transfer between services may incur charges.

7. **Amazon EC2 Instances:**
   Which of the following actions is NOT possible with Amazon EC2 instances?
   - A. Increasing the disk size of an EBS volume attached to an instance
   - B. Changing the instance type of a stopped instance
   - C. Moving an instance from one region to another
   - D. Taking a snapshot of an EBS volume attached to an instance
   > **Answer: C**
   > **Explanation:** While you can change the instance type of a stopped instance and modify the size of an EBS volume, you cannot move an instance from one region to another. You can, however, take a snapshot of an EBS volume and create a new instance in another region using that snapshot.

8. **AWS Service for Content Delivery:**
   What AWS service would you use to quickly distribute content to users around the world with low latency, high data transfer speeds, and no minimum usage commitments?
   - A. AWS Direct Connect
   - B. Amazon EFS
   - C. Amazon CloudFront
   - D. Amazon Route 53
   > **Answer: C**
   > **Explanation:** Amazon CloudFront is a content delivery network (CDN) service that securely delivers data, videos, applications, and APIs to customers globally with low latency, high transfer speeds, and no minimum usage commitments.

9. **Elastic Load Balancing:**
   What does Elastic Load Balancing do?
   - A. It automatically adjusts the number of EC2 instances handling application traffic.
   - B. It distributes incoming application traffic across multiple targets, such as EC2 instances, containers, and IP addresses.
   - C. It balances the storage load between multiple EBS volumes.
   - D. It balances the data load between different AWS regions.
   > **Answer: B**
   > **Explanation:** Elastic Load Balancing automatically distributes incoming application traffic across multiple targets, such as Amazon EC2 instances, containers, and IP addresses, in one or more Availability Zones.

10. **AWS Storage Services:**
    Which AWS service is a file storage service for use with Amazon EC2 instances?
    - A. Amazon EBS
    - B. Amazon EFS
    - C. Amazon S3
    - D. AWS Storage Gateway
   > **Answer: B**
   > **Explanation:** Amazon Elastic File System (EFS) is a file storage service for use with Amazon EC2. EFS provides a simple, scalable, fully managed elastic NFS file system for use with AWS Cloud services and on-premises resources.

### Set 7:

1. **AWS Budgets:**
   What AWS feature allows you to set custom budgets to track your cost and usage from the simplest to the most complex requirements?
   - A. AWS Cost Explorer
   - B. AWS Trusted Advisor
   - C. AWS Budgets
   - D. AWS Cost and Usage Report
   > **Answer: C**
   > **Explanation:** AWS Budgets gives you the ability to set custom budgets that alert you when your costs or usage exceed (or are forecasted to exceed) your budgeted amount.

2. **Disaster Recovery in AWS:**
   Which AWS service is primarily used for disaster recovery and backup of data?
   - A. Amazon S3
   - B. Amazon Glacier
   - C. AWS Storage Gateway
   - D. Amazon EBS
   > **Answer: B**
   > **Explanation:** Amazon Glacier (now known as Amazon S3 Glacier) is a secure, durable, and extremely low-cost storage service for data archiving and long-term backup. It's designed to deliver 99.999999999% durability and provides comprehensive security and compliance capabilities that can help meet even the most stringent regulatory requirements.

3. **AWS Global Infrastructure:**
   What are the main components of the AWS Global Infrastructure?
   - A. Regions, Availability Zones, and Edge Locations
   - B. Data Centers, Content Delivery Networks, and Databases
   - C. Compute, Storage, and Database services
   - D. Virtual Private Clouds, Subnets, and Endpoints
   > **Answer: A**
   > **Explanation:** AWS Global Infrastructure consists of Regions, Availability Zones, and Edge Locations. Regions are geographic locations around the world where AWS clusters data centers. Each AWS Region consists of multiple, isolated, and physically separate AZ's within a geographic area. Edge Locations are endpoints for AWS which are used for caching content for Amazon CloudFront.

4. **Amazon EC2 Auto Scaling:**
   What is the main benefit of Amazon EC2 Auto Scaling?
   - A. It automatically changes the EC2 instance types based on workload requirements.
   - B. It automates the process of adding or removing EC2 instances based on traffic or load.
   - C. It reduces the cost of EC2 instances by scaling down when the instances are not in use.
   - D. It increases the storage capacity of EC2 instances automatically.
   > **Answer: B**
   > **Explanation:** Amazon EC2 Auto Scaling helps you maintain application availability and allows you to automatically add or remove EC2 instances according to conditions you define, such as traffic or CPU utilization.

5. **AWS IAM Roles:**
   Why should you use IAM roles instead of sharing security credentials?
   - A. Roles provide more secure and flexible access to resources.
   - B. Roles allow you to have unlimited IAM users.
   - C. Roles enable users to have full administrative access.
   - D. Roles are easier to use because they do not require any credentials.
   > **Answer: A**
   > **Explanation:** IAM roles offer a more secure way to delegate access to users, services, and applications without the use of static access keys. Roles provide temporary security tokens for authentication, which can be automatically rotated and managed by AWS.

6. **AWS CloudTrail:**
   What does AWS CloudTrail primarily help with?
   - A. It helps with auditing and reviewing user actions and API usage.
   - B. It accelerates content delivery through a network of edge locations.
   - C. It balances the load across EC2 instances.
   - D. It automates software deployments to EC2 instances.
   > **Answer: A**
   > **Explanation:** AWS CloudTrail is a service that enables governance, compliance, operational auditing, and risk auditing of your AWS account. It allows you to log, continuously monitor, and retain account activity related to actions across your AWS infrastructure.

7. **Amazon VPC Peering:**
   What does a VPC peering connection allow you to do?
   - A. Connect one VPC with another VPC through a direct network route.
   - B. Peer a VPC with an on-premises data center.
   - C. Automatically replicate data across two VPCs.
   - D. Increase the bandwidth to the internet from a VPC.
   > **Answer: A**
   > **Explanation:** A VPC peering connection is a networking connection between two VPCs that enables you to route traffic between them using private IPv4 addresses or IPv6 addresses. Instances in either VPC can communicate with each other as if they are within the same network.

8. **AWS Cost Optimization:**
   What tool can help you with cost optimization by identifying unused and idle resources or instances with low utilization in AWS?
   - A. AWS Budgets
   - B. AWS Cost Explorer
   - C. AWS Trusted Advisor
   - D. Amazon CloudWatch
   > **Answer: C**
   > **Explanation:** AWS Trusted Advisor provides real-time guidance to help you provision your resources following AWS best practices. It can help you reduce cost by identifying unused and idle resources or instances with low utilization.

9. **Amazon DynamoDB:**
   Which of the following best describes Amazon DynamoDB?
   - A. It's a managed NoSQL database service.
   - B. It's a virtual server for hosting web applications.
   - C. It's a file storage service for EC2 instances.
   - D. It's a relational database service with a SQL interface.
   > **Answer: A**
   > **Explanation:** Amazon DynamoDB is a managed NoSQL database service that provides fast and predictable performance with seamless scalability. It allows you to create database tables that can store and retrieve any amount of data and serve any level of request traffic.

10. **AWS Elastic Beanstalk:**
    What is AWS Elastic Beanstalk primarily used for?
    - A. To manage user access and encryption keys.
    - B. To automatically manage the deployment of applications to the cloud.
    - C. To provide a managed desktop computing service in the cloud.
    - D. To facilitate direct, private connections between AWS and on-premises environments.
   > **Answer: B**
   > **Explanation:** AWS Elastic Beanstalk is an easy-to-use service for deploying and scaling web applications and services developed with Java, .NET, PHP, Node.js, Python, Ruby, Go, and Docker on familiar servers such as Apache, Nginx, Passenger, and IIS. You simply upload your code and Elastic Beanstalk automatically handles the deployment, from capacity provisioning, load balancing, auto-scaling to application health monitoring.
