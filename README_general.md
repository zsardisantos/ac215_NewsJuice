# NewsJuice (AC215 - Milestone 5)

> Personalized daily podcast summaries of Harvard-related news — built with a scalable RAG pipeline, real-time voice interaction, and user authentication.

---

## 👥 Team

- **Khaled Aly**
- **Zac Sardi-Santos**
- **Joshua Rosenblum**
- **Christian Michel**

**Team name:** `NewsJuice`

---

## 📚 Project Overview

**NewsJuice** is an application that generates a **customized podcasts** summarizing the latest news based on the user’s interests.
It is primarily designed for the **Harvard community**, pulling content from Harvard-related news sources.

## Explanation of the README-files organization

1. A decription of the main folders and files can be found in *README_Repository_Organization.md*

2. The main changes versus Milestone 4 can be found in *README_Changes_MS_4-MS_5.md*


3. A detailed description of Finetuning can be found in *docs/Finetuning_documentation/README.md*

4. *README_Deployment_Guide_GKS_pulumi* desribes how to deploy the app on a kubernetes cluster with pulumi. This covers the Milestone 5 deliverables "Kubernetes Deployment - Deploy the application to a Kubernetes cluster" and "Pulumi Infrastructure Code".

5. *README_Deployment_Guide_CI-CD.md* (complementary to the previous document) contains a description how to set up and run the CI-CD cycle with GitHub actions, triggering deployment on a kubernetes cluster with pulumi. This covers the Milestone 5 deliverable "CI/CD Pipeline Implementation (GitHub Actions)".

6. *README_Scaling_with_kybernetes* explains how the scaling of the app works, provides instructions for a load test, and shows some sample screenshot (k9s tool for visualization) of the (horizontal) scaling of additional pods. This covers the Milestong 5 deliverable "Demonstrate basic scaling ....". 


You will find READMEs also in the docs folder:

    a. A detailed description of the app in *docs/Application_Design_Document/APPLICATION_DESIGN.md*

    b. A detailed description of the CI/CD set-up in *docs/CI_CD_set-up_and_evidence/README_Deployment_Guide_CI-CD.md* 

    c. A detailed description of the Data Versioning approach can be found in *docs/Data_Versioning_documentation/README_data_versioning.md*


Each service contains a README with a more detailed description (includes also intructions for local testing and Cloud Run deployment for testing)
- README_loader_deployed
- README_scraper_deployed
- README_chatter_deployed


