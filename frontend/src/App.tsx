// src/App.tsx

import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import Header from "./components/Header"
import About from "./pages/About"
import Chat from "./pages/Chat"
import KnowledgeCenter from "./pages/KnowledgeCenter"

function App() {
  return (
    <Router>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<About />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/knowledge" element={<KnowledgeCenter />} />
        </Routes>
      </main>
    </Router>
  )
}

export default App
