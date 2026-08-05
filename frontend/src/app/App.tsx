import { QueryClientProvider } from "@tanstack/react-query";
import { NavigatorPage } from "../pages/navigator/NavigatorPage";
import { queryClient } from "./providers/queryClient";

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <NavigatorPage />
    </QueryClientProvider>
  );
}
