import "./styles.css";

export const metadata = {
  title: "Atlas | Enterprise AI Research Agent",
  description: "Evidence-first research workspace with complete citations, findings and metrics visualization.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen bg-[#030407] text-[#eff3fa] selection:bg-[#9ee8cf]/30 selection:text-[#9ee8cf]">
        {children}
      </body>
    </html>
  );
}
