// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyD3iJY5dmP9fTjTr_5Yntb7rHfw4doZQdI",
  authDomain: "aegis-fedb3.firebaseapp.com",
  projectId: "aegis-fedb3",
  storageBucket: "aegis-fedb3.firebasestorage.app",
  messagingSenderId: "265897521345",
  appId: "1:265897521345:web:cda0c905300659aff06440"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const storage = firebase.storage();