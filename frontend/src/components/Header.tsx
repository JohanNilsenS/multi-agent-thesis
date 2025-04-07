import { Link } from "react-router-dom"
import "../styles/Header.css"

export default function Header() {
  return (
    <header className="header">
      <nav className="nav">
        <div className="logo">Multi-Agent System</div>
        <ul className="nav-links">
          <li><Link to="/">About</Link></li>
          <li><Link to="/chat">Demonstration</Link></li>
        </ul>
      </nav>
    </header>
  )
}
