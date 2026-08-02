import {Outlet} from "react-router-dom";

const AuthLayout = () => {
  return (
    <div style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}>
      <Outlet />
    </div>
  );
};

export default AuthLayout;