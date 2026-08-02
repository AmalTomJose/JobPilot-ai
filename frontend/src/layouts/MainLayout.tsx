import {Outlet} from "react-router-dom";
import Sidebar from "../components/Sidebar/Sidebar";
import Navbar from "../components/Navbar/Navbar";

const MainLayout = () => {
    return (
        <>
          <Navbar />
        <div
        style={{
            display: "flex",
        }}
        >
        <Sidebar />

        <main
            style={{
            flex: 1,
            padding: "20px",
            }}
        >
            <Outlet />
        </main>
        </div>
        </>
    )
}

export default MainLayout;