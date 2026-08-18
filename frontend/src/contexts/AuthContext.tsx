import {
    createContext,
    useState,
    useEffect,
    type ReactNode,
} from "react";

import type { User } from "../types/user.types";
import type { LoginResponse } from "../types/auth.types";
import { authService } from "../services/auth.service";


type AuthContextType = {
    user: User | null;
    isAuthenticated: boolean;
    loading:boolean,
    login: (response: LoginResponse) => void;
    logout: () => void;
};


export const AuthContext =
    createContext<AuthContextType | undefined>(undefined);


type AuthProviderProps = {
    children: ReactNode;
};


export function AuthProvider({
    children,
}: AuthProviderProps) {

    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(()=>{
        const restoreUser = async ()=>{
            const token =localStorage.getItem("access_token");
            if(!token){
                setLoading(false);
                return;
            }
            try{
                const currentUser=await authService.getCurrentUser();
                setUser(currentUser);
            }
            catch(error){
                console.error("Failed to restore user:", error);
                localStorage.removeItem("access_token");
                setUser(null);
            }
            finally{
                setLoading(false);
            }
        }
        restoreUser();
    },[]);


    const login = (response: LoginResponse) => {

        localStorage.setItem(
            "access_token",
            response.access_token
        );
        console.log("userlogin:", response.user);

        setUser(response.user);
    };


    const logout = () => {

        localStorage.removeItem("access_token");

        setUser(null);
    };


    const isAuthenticated = user !== null;


    return (
        <AuthContext.Provider
            value={{
                user,
                isAuthenticated,
                loading,
                login,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}