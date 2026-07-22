import { Fragment } from 'react'
import priceData from '../data/price.json'
import type { PriceSnapshot } from '../types'
import './MissionPage.css'

// Ported from SLC-DASHBOARD-2024/SLC/Validator_Mission.ipynb ("Our Mission",
// "Our Recognition", "Economic Incentives" and the surrounding About-us
// copy). The old notebook cited a handful of live figures inline (32 ETH's
// USD equivalent, plus a "Crypto Market Caps" section). Both are now wired
// to price.json (see scripts/fetch_price.py): the old CoinMarketCap key
// hazard was dropped in favor of CoinGecko's public /simple/price + /global
// endpoints, which checked out as keyless in the old repo too — none of
// get_total_crypto_market_cap()/get_BTC_market_cap()/get_eth_market_cap()
// ever used an API key, so there was nothing to carry over, just endpoints
// to re-implement.

const price = priceData as PriceSnapshot

function formatUsd(usd: number) {
  return usd.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

function formatUsdCompact(usd: number) {
  return usd.toLocaleString(undefined, {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 2,
  })
}

interface PoapBadge {
  title: string
  imageUrl: string
  description: string
}

const poapBadges: PoapBadge[] = [
  {
    title: 'August 2020 — Medalla Testnet Recovery',
    imageUrl: 'https://assets.poap.xyz/medalla-testnet-resuscitator-2020-logo-1598019050780.png',
    description:
      "In August 2020, the Medalla Testnet encountered challenges that threatened its operational continuity. This was one of the final Proof-of-Stake test networks before Ethereum 2.0 went live on mainnet. Our swift and decisive actions during this period were crucial in restoring the testnet to full functionality. This POAP commemorates our technical agility and the trust placed in us by the Ethereum community, highlighting our role as reliable node operators committed to maintaining the network's resilience.",
  },
  {
    title: 'November 2020 — Medalla Genesis Validator (Prysm)',
    imageUrl: 'https://assets.poap.xyz/medalla-testnet-genesis-validator-prysm-client-2020-logo-1595438201727.png',
    description:
      'Our proactive involvement as Genesis Validators with the Prysm client in November 2020 marks our early and impactful contribution to Ethereum’s proof-of-stake journey. This POAP is a badge of our technical expertise and our pioneering efforts during the nascent stage of Ethereum 2.0, symbolizing our dedication to fostering a scalable and secure blockchain network.',
  },
  {
    title: '2022 — Beacon Chain First 32,769 Block Validators',
    imageUrl: 'https://assets.poap.xyz/beacon-chain-first-32769-block-validators-2021-2021-logo-1611528225519.png',
    description:
      "The September 2022 Beacon Chain First 32,769 Block Validators POAP honors our participation in one of Ethereum 2.0's foundational milestones. By being among the initial validators to propose blocks on the newly launched Beacon Chain, we have solidified our place in the annals of Ethereum's history. This POAP affirms our commitment to supporting the evolution of the Ethereum network and the larger blockchain ecosystem.",
  },
  {
    title: '2022 — Merge: Ethereum Staking Node Operator',
    imageUrl: 'https://assets.poap.xyz/eth-staking-node-operator-at-the-time-of-the-merge-2022-logo-1670377283075.png',
    description:
      'The merge of the Proof-of-Work blockchain into the Proof-of-Stake blockchain. This POAP certifies that we were operating an Ethereum staking node at the time of the merge, thus helping decentralize Ethereum. This generally means you are either a solo staker or a Rocket Pool node operator.',
  },
]

interface MarketCapStat {
  label: string
  valueUsd: number | null
  sourceNote: string
}

const marketCapStats: MarketCapStat[] = [
  { label: 'total crypto market cap', valueUsd: price.totalCryptoMarketCapUsd, sourceNote: 'source: CoinGecko /global' },
  { label: "bitcoin's market cap", valueUsd: price.btcMarketCapUsd, sourceNote: 'source: CoinGecko /simple/price' },
  { label: "ethereum's market cap", valueUsd: price.ethMarketCapUsd, sourceNote: 'source: CoinGecko /simple/price' },
]

export function MissionPage() {
  return (
    <div className="mission-page">
      <header className="mission-page__hero">
        <span className="mission-page__eyebrow">SLC · About</span>
        <h1 className="mission-page__title">Our Mission</h1>
      </header>

      <section className="mission-page__section">
        <div className="mission-page__section-body">
          <p>
            At SL Consulting, our mission is to democratize access to the world of blockchain technology and
            Ethereum staking. We understand that the intricacies of blockchain can be daunting for the average
            individual. That&apos;s why we specialize in creating, managing, and running Ethereum validators that
            are accessible to everyone. We recognize that setting up a validator on the Ethereum network requires
            a substantial commitment &ndash; specifically, a stake of 32 ETH (~{formatUsd(32 * price.ethUsd)}). This threshold can be a
            significant barrier for many. To address this, we offer a unique pooling solution, allowing
            individuals to participate in staking without needing the full 32 ETH.
          </p>
          <p>
            As a staking pool, we accumulate ETH contributions from our clients, combining these with our rewards
            until we reach the required amount to set up a new validator. This approach not only lowers the entry
            barrier but also allows participants to benefit from the rewards of staking. Our system is designed to
            be inclusive, offering an opportunity for those who might otherwise be unable to participate.
          </p>
          <p>
            Choosing SL Consulting for your ETH staking needs means embracing personal control, privacy, and
            flexibility. Our clients enjoy complete control over their assets, with customized terms that align
            with their individual needs, far removed from the one-size-fits-all approach of platforms like
            Coinbase or Binance. Our commitment to privacy ensures your information remains confidential, and our
            flexible staking and unstaking options offer unparalleled freedom compared to traditional staking
            pools.
          </p>
          <p>
            Our service reduces the risks associated with platform-specific failures, breaches, or regulatory
            changes while maximizing your return. With potentially lower fees and direct involvement in
            Ethereum&apos;s security, our clients contribute to a decentralized future while gaining deeper
            insights into blockchain technology. At SL Consulting, we believe in building personal, trust-based
            relationships, providing our clients with a sense of security and peace of mind in the rapidly
            evolving world of Ethereum staking.
          </p>
          <p>
            SL Consulting offers a unique opportunity for direct investment and ownership in active Ethereum
            validators. When you stake with us, you&apos;re not just some funds mixed in a blender; you&apos;re
            directly linked to a validator on the network. This direct involvement not only brings you closer to
            the Ethereum ecosystem but also ensures that any tips received by the validator are proportionally
            distributed to that validator&apos;s investors. Your stake in our validators means direct benefits
            from their performance, and our 365-day APY of 5.17% is a testament to our commitment to your
            financial success. Our top validator sits at over a 20% ROI on the 3 years it&apos;s been validating
            the network.
          </p>
          <p>
            Our approach to rewards sets us apart from the competition. We&apos;re proud of our track record in
            compounding rewards, a strategy that has shown tangible results in the growth of our validators. This
            method of reinvesting rewards into future validators has been successfully implemented in at least two
            validators already, amplifying the earning potential for our clients. It&apos;s not just about
            staking; it&apos;s about strategically growing your investment and seeing real returns, as evidenced
            by our impressive returns!
          </p>
          <p>
            At SL Consulting, we also understand the importance of a competitive fee structure. Our fee of 18% on
            staking rewards is significantly lower than what you might find with larger platforms like Coinbase,
            Kraken, or Lido. This lower fee means more of the staking rewards end up in your pocket, making your
            investment with us not only a smart choice for direct blockchain involvement but also a more
            profitable one in the long run, as reflected in our historical data.
          </p>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>Our Recognition</h2>
        </header>
        <div className="mission-page__section-body">
          <div className="mission-page__badges">
            {poapBadges.map((badge) => (
              <figure className="mission-page__badge" key={badge.title}>
                <img src={badge.imageUrl} alt={badge.title} loading="lazy" />
                <figcaption>{badge.title}</figcaption>
              </figure>
            ))}
          </div>
          <dl className="mission-page__badge-details">
            {poapBadges.map((badge) => (
              <Fragment key={badge.title}>
                <dt>{badge.title}</dt>
                <dd>{badge.description}</dd>
              </Fragment>
            ))}
          </dl>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>Economic Incentives</h2>
        </header>
        <div className="mission-page__section-body">
          <p>
            Running an Ethereum validator is more than a financial endeavor; it&apos;s a commitment to upholding
            the network&apos;s integrity and efficiency. As validators, we are entrusted with the task of
            processing a series of transactions and creating new blocks, a role that places us at the heart of
            the network&apos;s operations.
          </p>
          <div className="mission-page__incentive">
            <h3>Base Rewards</h3>
            <p>
              The base reward is a fundamental component of the staking rewards mechanism. It&apos;s distributed
              to validators every day for carrying out their duties, which include proposing and attesting to
              blocks. The size of the base reward is adjusted algorithmically and is influenced by the total
              amount of ETH staked on the network &ndash; typically around 2&ndash;4% APR.
            </p>
          </div>
          <div className="mission-page__incentive">
            <h3>Tips</h3>
            <p>
              Tips are additional rewards that users pay to prioritize their transactions in a block. When the
              network is congested, users can add a tip to their transaction to incentivize validators to include
              it more quickly in a block. Validators receive these tips for blocks they propose and have selected
              for network inclusion. The validator that is picked to propose a block is selected in a
              nondeterministic manner. Our historical return varies from 1&ndash;6% APR from tips.
            </p>
          </div>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>The Future of Finance &mdash; Staking on Ethereum</h2>
        </header>
        <div className="mission-page__section-body">
          <p>
            Our commitment as a staking pool on Ethereum&apos;s blockchain is deeply rooted in our support for the
            Ethereum network, a symbol of defiance against censorship and a living embodiment of principles such
            as immutability and transparency. This steadfast network offers an extraordinary feature: it allows
            anyone to create an account on its public distributed ledger. This inclusivity is a cornerstone of
            Ethereum&apos;s design, ensuring that no user can be excluded or banned from utilizing the network.
          </p>
          <p>
            This open-access philosophy extends to Ethereum&apos;s smart contracts. By enabling universal
            participation, Ethereum democratizes financial opportunities, allowing users from all walks of life to
            engage with its smart contracts. These contracts operate on a framework of unbiased automation,
            executing transactions and agreements with unerring accuracy, irrespective of the user&apos;s identity
            or location. This level of inclusivity and fairness is unprecedented in traditional financial
            systems.
          </p>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>Advantages of Blockchains Over CBDCs</h2>
        </header>
        <div className="mission-page__section-body">
          <p>
            Public blockchains offer a level of transparency, inclusivity, and decentralization that Central Bank
            Digital Currencies simply cannot match. Unlike CBDCs, which are controlled by central authorities and
            often subject to the whims of governmental policies, public blockchains operate on a global scale,
            unbound by national borders or centralized control. This decentralized nature ensures that
            transactions and interactions are not only transparent but also free from unilateral control or
            manipulation. Public blockchains empower individuals by giving them direct control over their assets
            without the need for intermediaries. In contrast, CBDCs, while digitized, still replicate many of the
            limitations and controls inherent in traditional fiat currencies, including potential surveillance
            and restrictions on use.
          </p>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>Crypto Market Caps</h2>
        </header>
        <div className="mission-page__section-body">
          <div className="mission-page__stats">
            {marketCapStats.map((stat) => (
              <dl className="mission-page__stat" key={stat.label}>
                <dt>{stat.label}</dt>
                <dd className={stat.valueUsd === null ? 'mission-page__stat--unavailable' : undefined}>
                  {stat.valueUsd === null ? 'unavailable' : formatUsdCompact(stat.valueUsd)}
                </dd>
                <span className="mission-page__stat-sub">{stat.sourceNote}</span>
              </dl>
            ))}
          </div>
          <div className="mission-page__notice">
            <span className="mission-page__notice-label">live figures, refreshed at build time</span>
            <p>
              The original notebook pulled these figures live from CoinGecko and CryptoCompare on every page
              load. This static site can&apos;t do that (no runtime API calls, see this repo&apos;s
              architecture) &mdash; instead they&apos;re fetched by <code>scripts/fetch_price.py</code> and
              baked into the build, same as every other figure on this site. All three now come from
              CoinGecko&apos;s public endpoints (<code>/simple/price</code>, <code>/global</code>) with no API
              key required &mdash; the old CryptoCompare calls needed none either, so nothing carried forward
              from the old repo, just re-implemented endpoints. Re-run the fetch script to refresh.
            </p>
          </div>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>Proof of Stake for a Sustainable Blockchain Future</h2>
        </header>
        <div className="mission-page__section-body">
          <p>
            Our preference for Proof of Stake over the traditional Proof of Work model is rooted in its
            environmental sustainability, security enhancements, and minimal hardware requirements. PoS reduces
            the massive energy consumption associated with PoW, making blockchain technology more sustainable and
            environmentally friendly. This shift is crucial in a world increasingly aware of the impact of human
            activities on the climate. PoS also democratizes the validation process, allowing for broader
            participation with less financial barrier to entry compared to the costly hardware required for PoW
            mining. Additionally, PoS networks tend to offer enhanced security and reduced risk of centralization,
            as they are less prone to the computational power concentration seen in PoW systems.
          </p>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>Shaping the Future, Beyond Traditional Finance</h2>
        </header>
        <div className="mission-page__section-body">
          <p>
            Ethereum&apos;s blockchain, particularly with its transition to PoS, represents an early network with
            immense growth and network effect potential. Its ability to execute smart contracts and support
            decentralized applications positions it as a foundational technology for a new financial ecosystem.
            Unlike traditional finance, which is often bogged down by bureaucracy, inefficiency, and accessibility
            barriers, Ethereum offers a more open, efficient, and inclusive alternative. This blockchain empowers
            users with self-sovereign finance, where transactions are not only faster and cheaper but also
            transparent and secure. The future of finance, as we envision it, will be built on the principles of
            decentralization and democratization, with Ethereum leading the charge in reshaping how we think about
            and interact with financial systems.
          </p>
        </div>
      </section>

      <section className="mission-page__section">
        <header className="mission-page__section-header">
          <h2>Join Our Staking Pool</h2>
        </header>
        <div className="mission-page__section-body">
          <p>
            A service to the network and an investment in the future: our staking pool is not just a collective
            investment but a service to the greater Ethereum network. By joining us, you become part of a
            community that is laying the foundation for a more open, resilient, and user-empowered blockchain
            ecosystem. Your participation helps to decentralize the network further, enhancing its security and
            stability, which is vital for the continued growth and adoption of Ethereum. Together, we are not
            only maximizing our potential rewards but also contributing to a groundbreaking technology that is
            reshaping the financial landscape. We invite you to be part of this exciting journey, to stake with
            us, and to witness firsthand the evolution of blockchain technology and its far-reaching implications
            for the future.
          </p>
        </div>
      </section>

      <div className="mission-page__disclaimer">
        <span className="mission-page__disclaimer-label">Disclaimer</span>
        <p>
          The information provided on this page, including any figures related to initial investments and
          returns, is for illustrative purposes only. These numbers are estimates and should not be considered as
          precise or absolute. Market conditions, investment strategies, and other factors can influence actual
          performance, and therefore actual outcomes may vary. We recommend consulting with a financial advisor
          before making investment decisions. This page is not intended to provide specific financial,
          investment, tax, legal, or accounting advice.
        </p>
      </div>
    </div>
  )
}
