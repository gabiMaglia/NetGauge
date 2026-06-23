import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { TrustBar } from './components/TrustBar';
import { Problem } from './components/Problem';
import { Features } from './components/Features';
import { HowItWorks } from './components/HowItWorks';
import { Privacy } from './components/Privacy';
import { Advanced } from './components/Advanced';
import { Comparison } from './components/Comparison';
import { Download } from './components/Download';
import { Faq } from './components/Faq';
import { CtaFinal } from './components/CtaFinal';
import { Footer } from './components/Footer';

function App() {
  return (
    <>
      <a href="#main-content" className="skip-link">
        Saltar al contenido principal
      </a>
      <Header />
      <main id="main-content">
        <Hero />
        <TrustBar />
        <Problem />
        <Features />
        <HowItWorks />
        <Privacy />
        <Advanced />
        <Comparison />
        <Download />
        <Faq />
        <CtaFinal />
      </main>
      <Footer />
    </>
  );
}

export default App;
