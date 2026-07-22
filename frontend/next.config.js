/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    // react-pdf(pdfjs-dist)가 참조하는 node 전용 canvas 모듈을 브라우저 빌드에서 제외
    config.resolve.alias.canvas = false;
    return config;
  },
};

module.exports = nextConfig;
