# Deployment Architecture (AWS)

This document describes how Whatcommerce is deployed in AWS for the `dev` environment.

## Network and compute topology

```mermaid
flowchart TB
  Internet((Internet))

  subgraph AWS[AWS Account / Region]
    subgraph VPC[VPC]
      subgraph PubA[Public Subnet A]
        ALB[Application Load Balancer]
      end
      subgraph PubB[Public Subnet B]
        ALB2[ALB AZ peer]
      end

      subgraph PrivA[Private Subnet A]
        API1[API EC2 Instance\n(ASG)]
        WRK1[Worker EC2 Instance\n(ASG)]
      end
      subgraph PrivB[Private Subnet B]
        API2[API EC2 Instance\n(ASG)]
        WRK2[Worker EC2 Instance\n(ASG)]
      end

      NAT[NAT Gateway]
    end

    RDS[(RDS PostgreSQL)]
    Uploads[(S3 Uploads Bucket)]
    WebBucket[(S3 Web Bucket)]
    CF[CloudFront Distribution]
    SM[Secrets Manager]
    ACM[ACM Certificate]
    R53[Route53 Hosted Zone]
  end

  Internet -->|HTTPS api.*| R53
  Internet -->|HTTPS whatcommerce.*| R53
  R53 --> CF
  R53 --> ALB
  CF --> WebBucket
  ALB --> API1
  ALB --> API2
  API1 --> RDS
  API2 --> RDS
  API1 --> Uploads
  API2 --> Uploads
  API1 --> SM
  API2 --> SM
  WRK1 --> SM
  WRK2 --> SM
  WRK1 --> API1
  WRK2 --> API2
  PrivA --> NAT
  PrivB --> NAT
  NAT --> Internet
  ACM --> ALB
  ACM --> CF
```

## Domain routing

```mermaid
flowchart LR
  U[User Browser] -->|https://whatcommerce.play.jaraflytech.com| CF[CloudFront]
  CF --> S3W[S3 Static Web Bucket]
  U -->|https://api.play.jaraflytech.com| ALB[API ALB]
  ALB --> API[API ASG instances]
  API --> RDS[(RDS Postgres)]
  API --> S3U[(S3 Uploads)]
```

## CI/CD and instance refresh flow

```mermaid
sequenceDiagram
  participant Dev as Developer
  participant GH as GitHub Actions
  participant IAM as AWS OIDC Role
  participant S3 as S3 Web Bucket
  participant CF as CloudFront
  participant ASG as Worker ASG

  Dev->>GH: Push to main / run deploy-dev workflow
  GH->>IAM: Assume role via OIDC
  GH->>S3: Sync web/out
  GH->>CF: Create invalidation
  GH->>ASG: Start instance refresh
  ASG-->>GH: Refresh status (poll until Successful)
```

## Boot-time configuration flow

```mermaid
flowchart LR
  LT[Launch Template user_data] --> EC2[EC2 Instance Boot]
  EC2 --> SM[Read .env from Secrets Manager]
  SM --> APIENV[API .env on instance]
  SM --> WENV[Worker .env on instance]
  APIENV --> APISVC[systemd API service]
  WENV --> WRKSVC[systemd worker service]
  APISVC --> ALB[Target group health checks]
```

## Notes

- API instances are private and only reachable through the ALB security group.
- Worker instances are private and egress-only; they communicate outbound to WhatsApp/OpenAI/API.
- RDS is private and restricted to API security group access.
- CloudFront serves the static web app from S3 and handles edge caching.
- Secrets are injected at boot from Secrets Manager; runtime `.env` files are not stored in git.
