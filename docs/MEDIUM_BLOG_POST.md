# Beyond the Play Button: Reinventing University News with Interactive Audio

**By the NewsJuice Team**

*Estimated Reading Time: 5 min*

---

In an era defined by information overload, staying connected to your campus community is harder than it should be. Students, faculty, and alumni are bombarded with newsletters, emails, and headlines, yet often feel disconnected from the stories that matter. We doomscroll through updates and passively listen to podcasts while commuting. But what happens when you have a question about a new campus policy or a breakthrough research paper?

With traditional media, you hit a wall. The podcast host can't hear you. The article can't answer your follow-up questions.

We built **NewsJuice** to break that wall. We wanted to create an experience where "consuming campus news" transforms into "having a conversation."

## The Problem: The One-Way Street of Campus Media

The fundamental limitation of current digital media is its linearity. Whether it's a 30-minute interview with a professor or a 5-minute daily briefing, the flow of information is unidirectional: from the creator to the consumer.

This creates two major issues:
1.  **Lack of Personalization:** You hear what everyone else hears, regardless of your specific major, interests, or prior knowledge.
2.  **Passive Engagement:** Without the ability to interact, retention drops, and the nuance of complex university topics is lost.

We asked ourselves: *What if a news app could listen back?*

## The Solution: An AI Host for the Academic Community

NewsJuice is not just a podcast app; it's a real-time, bidirectional audio platform focused on university news. We are launching first with **Harvard University**, aggregating sources from *The Harvard Crimson*, *Harvard Gazette*, and official university announcements to create a unified, interactive audio experience.

At its core is "NJ," an AI host that doesn't just read the headlines—it discusses them with you.

Imagine listening to a segment about a new policy on foreign student enrollment. Instead of just absorbing facts, you press a button and ask, *"Wait, how does this compare to the policy from 2020?"*

The audio stream pauses. The AI processes your voice, understands the context, retrieves relevant historical data from the university archives, and seamlessly weaves an answer into the ongoing narrative. It’s like having a knowledgeable peer sitting in the passenger seat.

![Image Instruction: Create an image using this prompt: "A high-tech split-screen composition. LEFT SIDE: A digital network of glowing nodes and floating glass screens displaying 'The Harvard Crimson' and 'Harvard Gazette' logos, connected by deep crimson data streams. RIGHT SIDE: A sleek modern smartphone showing the NewsJuice app interface, featuring a vibrant, pulsing pink and purple 3D orb in the center. The crimson data streams from the left flow smoothly into the phone on the right, merging into the glowing orb. Cinematic lighting, 8k resolution, unreal engine 5 render, dark background with neon accents."]

## Under the Hood: The Technical Symphony

Building a real-time voice conversation interface requires orchestrating multiple complex technologies with near-zero latency. Here is how we engineered the solution.

### 1. The Frontend: React & The "Living" Interface
We built the frontend using **React** and **Vite** for speed. But an audio app needs to *feel* alive. We used **Framer Motion** to create our centerpiece: the "Animated Orb."

This orb isn't just a pretty visual; it's a state machine visualizer. It pulses gently when listening, swirls rapidly when processing, and modulates its glow in sync with the AI's voice during playback. This provides immediate, intuitive feedback to the user in a voice-first interface.

### 2. The Real-Time Pipeline: WebSockets & Audio Processing
HTTP requests are too slow for conversation. We implemented a **WebSocket** architecture to handle full-duplex communication.

*   **Input:** We use the browser's `AudioContext` API to capture raw PCM audio data from the microphone. This is streamed in chunks to our backend, ensuring that we don't have to wait for the user to finish speaking before we start processing.
*   **Output:** The AI's response is streamed back as audio bytes, which we buffer and play immediately, minimizing the "awkward silence" typical of voice assistants.

![Image Instruction: A high-level architecture diagram.
1. User speaks -> Browser (AudioContext)
2. Browser -> WebSocket Stream -> Python Backend (FastAPI)
3. Backend -> Speech-to-Text Service -> LLM (Context & RAG) -> Text-to-Speech Service
4. Audio Stream -> Browser -> User hears response]

### 3. The Backend: Python & Intelligent Orchestration
Our backend, built with **Python (FastAPI)** and hosted on **Google Cloud Run**, acts as the conductor. When audio arrives, it triggers a multi-step pipeline:
1.  **Transcribing:** Converting speech to text.
2.  **Reasoning:** An LLM analyzes the text against the current conversation context and retrieves relevant news data (RAG - Retrieval Augmented Generation).
3.  **Synthesizing:** Generating natural-sounding speech from the AI's textual response.

We also integrated **Firebase Auth** for secure user management and **CloudSQL** to store user preferences and conversation history, allowing the AI to "remember" you over time.

## The Impact: Democratizing Access to Knowledge

The implications of this technology extend far beyond convenience. By making university news interactive, we are making it more accessible and engaging.

*   **For Students:** Actively question administrative changes or research breakthroughs, turning passive listening into active learning.
*   **For Alumni:** Stay connected to the campus pulse with personalized updates that matter to you.
*   **For the Community:** A voice-first interface offers a complete news experience accessible to everyone, regardless of visual ability.

## What's Next?

While we are starting with **Harvard University**, our vision is to expand NewsJuice to universities everywhere. We are building a platform that can ingest and index news from any academic institution, creating a network of interactive, campus-specific AI hosts.

We are also working on **Settings & Personalization**, allowing users to tweak everything from the AI's speaking rate to the visual style of the interface (as seen in our new Orb Selector feature!).

NewsJuice is more than an app; it's a glimpse into the future of campus media. A future where we don't just consume stories—we are part of them.

---

*The NewsJuice project was built by Zac Sardi-Santos, Josh Rosenblum, Khaled Aly, and Christian Michel.*
