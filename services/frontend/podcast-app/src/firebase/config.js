// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyBgsCjTT1B_qZUioacHrLHcs5v0tXcmr2c",
  authDomain: "newsjuice-123456.firebaseapp.com",
  projectId: "newsjuice-123456",
  storageBucket: "newsjuice-123456.firebasestorage.app",
  messagingSenderId: "919568151211",
  appId: "1:919568151211:web:87459d5aabfe4d5ec8fdee"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth
export const auth = getAuth(app);

