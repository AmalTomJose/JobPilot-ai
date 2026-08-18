import { useAuth } from "../../hooks/useAuth";

const Navbar = () => {
  
  const {user,logout} = useAuth();
  console.log("USER:", user);
    return (
      <nav
        style={{
          height: "60px",
          background: "#1f2937",
          color: "white",
          display: "flex",
          alignItems: "center",
          padding: "0 20px",
        }}
      >
        <h2>JobPilot AI</h2>
        <h1>{user?.name ? user.name : "Normal value"}</h1>
        <button onClick = {logout}>Logout Fucker!!!!!</button>
      </nav>
    );
  };
  
  export default Navbar;