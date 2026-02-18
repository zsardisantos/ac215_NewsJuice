// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDxi2B1eGuc8yAsjRJHVv8XuHZUqbABbus",
  authDomain: "newsjuice-2.firebaseapp.com",
  projectId: "newsjuice-2",
  storageBucket: "newsjuice-2.firebasestorage.app",
  messagingSenderId: "364750432293",
  appId: "1:364750432293:web:1a38ce2ca92ef15e02f7cc",
  measurementId: "G-ZNY65FQ2YN"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Auth
export const auth = getAuth(app);

