# 📆 NewsJuice (AC215 - Milestone 4)


## 👥 Team

- **Khaled Aly**
- **Zac Sardi-Santos**
- **Joshua Rosenblum**
- **Christian Michel**

**Team name:** `NewsJuice`

---

## 📚 Overview of changes versus Milestone 3

**Scraper service**  
- Expanded to include all Harvard major news sources accross different schools
- Converted into an API 
- Deployed on Cloud Run and Scheduler (currently live deployed, running every 24h)
- Unit test added, covering every source scraper 

**Loader service**
- Changed embedding to VertexAI
- Deployment with Cloud Run and Scheduler (currently live deployed, running every 24h)
- Full test suite added (unit, integration and system) + CI workflow with GitHub Actions implemented

**Chatter service**
- Changed embedding to VertexAI
- Voice to text and text to voice implemented in streaming mode

**Frontend** 
- Newly implemented with Firebase
- User registration and authentication

**Other**
- Dataversioning implemented for SQL DB
- Finetuning of LLM (but decided to discard in app)
