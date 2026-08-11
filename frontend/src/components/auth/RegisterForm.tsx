import { Link } from "react-router-dom";
import {useForm} from "react-hook-form";
import type {RegisterFormData} from "../../types/auth.types";
import { registerSchema } from "../../schemas/auth.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { authService } from "../../services/auth.service";



const RegisterForm = () => {
  const{register,
  handleSubmit,formState:{errors,isSubmitting}} = useForm<RegisterFormData>({
      resolver: zodResolver(registerSchema)
  })

  const onSubmit = async (data:RegisterFormData) => {
    let response = await authService.register(data)
    console.log(response)
  }


  return (
    <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8">

      <h2 className="text-3xl font-bold text-center">
        Create Account
      </h2>

      <form className="mt-8 space-y-5" onSubmit={handleSubmit(onSubmit)}>

        <input
          type="text"
          {...register("name")}
          placeholder="Full Name"
          className="w-full border rounded-lg p-3"
        />
        {errors.name && (
          <p>{errors.name.message}</p>
        )}

        <input
          {...register("email")}

          placeholder="Email"
          className="w-full border rounded-lg p-3"
        />
         {errors.email && (
          <p>{errors.email.message}</p>
        )}

        <input
        type="password"
          {...register("password")}
          placeholder="Password"
          className="w-full border rounded-lg p-3"
        />
         {errors.password && (
          <p>{errors.password.message}</p>
        )}

        <input
        type="password"
          {...register("confirmPassword")}
          placeholder="Confirm Password"
          className="w-full border rounded-lg p-3"
        />
         {errors.confirmPassword && (
          <p>{errors.confirmPassword.message}</p>
        )}

        <label className="flex gap-2 items-center">

          <input type="checkbox" {...register("acceptTerms")}/>
          {errors.acceptTerms && (
                        <p className="text-red-500 text-sm mt-1">
                            {errors.acceptTerms.message}
                        </p>
                    )}

          I agree to the Terms & Conditions

        </label>

        <button
        type = "submit"
        disabled = {isSubmitting}
        className="w-full bg-blue-600 text-white rounded-lg p-3 hover:bg-blue-700"
          

        >
          {isSubmitting ? "Registering..." : "Register"}
        </button>

      </form>

      <p className="text-center mt-6">

        Already have an account?

        <Link
          to="/login"
          className="text-blue-600 ml-2"
        >
          Login
        </Link>

      </p>

    </div>
  );
};

export default RegisterForm;