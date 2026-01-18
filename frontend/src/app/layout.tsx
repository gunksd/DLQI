import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "@/styles/globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "DLQI - 机器学习量化交易平台",
  description: "基于机器学习的量化交易策略系统 - 毕业设计展示",
  keywords: ["量化交易", "机器学习", "LSTM", "金融科技", "回测系统"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <div className="min-h-screen bg-mesh">
          {children}
        </div>
      </body>
    </html>
  );
}
