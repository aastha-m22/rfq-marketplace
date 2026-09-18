import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  const isBuyer = user?.role === 'buyer'

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <NavLink to="/" className="brand">
            RFQ<span>Marketplace</span>
          </NavLink>

          {user && (
            <>
              {/* Navigation is role-specific: a buyer never sees supplier
                  screens and vice versa. The API enforces this too. */}
              <nav className="nav">
                {isBuyer ? (
                  <>
                    <NavLink to="/buyer/rfqs">My RFQs</NavLink>
                    <NavLink to="/buyer/rfqs/new">Post an RFQ</NavLink>
                  </>
                ) : (
                  <>
                    <NavLink to="/browse">Browse RFQs</NavLink>
                    <NavLink to="/my-quotations">My Quotations</NavLink>
                  </>
                )}
              </nav>

              <div className="topbar-user">
                <span className="user-meta">
                  <strong>{user.name}</strong>
                  <em>{user.role}</em>
                </span>
                <button className="btn btn-ghost" onClick={handleLogout}>
                  Log out
                </button>
              </div>
            </>
          )}
        </div>
      </header>

      <main className="container">
        <Outlet />
      </main>

      <footer className="footer">
        <p>Mini B2B RFQ Marketplace</p>
      </footer>
    </div>
  )
}
