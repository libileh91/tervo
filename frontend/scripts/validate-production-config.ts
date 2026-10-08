import { validateProductionApiBase } from "../src/api/urlConfig";

validateProductionApiBase(process.env.VITE_API_BASE_URL);
