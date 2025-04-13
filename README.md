# OpenSocialMonitor

**OpenSocialMonitor** is an open-source toolkit for detecting and monitoring automated manipulation on social media platforms. By identifying bot accounts and coordinated inauthentic behavior, it helps combat misinformation and manipulation campaigns.

## 📊 Why This Matters

Social media platforms have become battlegrounds where automated accounts manipulate public opinion and spread misinformation. This manipulation:

- Undermines democratic discourse
- Amplifies extremist viewpoints
- Creates false perception of consensus
- Overwhelms genuine user engagement

OpenSocialMonitor provides transparent, community-driven tools to expose this manipulation and level the playing field. This project takes no political stance - we believe people should be free to vote for and support any candidate or cause they choose. However, we also believe society has a responsibility to ensure everyone can form their opinions based on authentic information, not automated manipulation or coordinated disinformation campaigns.

## ⚠️ Important Warning

Please be aware that frequent API calls or automated interactions with social media platforms may trigger their anti-scraping measures or be interpreted as suspicious activity. This could potentially lead to rate limiting, temporary blocks, or even permanent suspension of your account.

**Recommendation:** Do not use your personal social media accounts with this tool. Instead, create dedicated accounts specifically for monitoring purposes. This separation helps protect your personal accounts and online presence.

Additionally, be mindful of API rate limits and implement reasonable delays between requests to minimize the risk of being flagged by platform security systems.

## 🚀 Features

- **Bot Detection**: Identifies potential automated accounts using behavioral and linguistic markers
- **Coordination Detection**: Discovers networks of accounts working together to spread identical content
- **Cross-Platform Support**: Initially focused on Instagram, with architecture to expand to other platforms
- **Warning System**: Alerts users about potential manipulation through reply comments
- **Open & Transparent**: All detection methods are open to scrutiny and improvement

## 📋 Making Real-World Impact

### For Journalists & Fact-Checkers
Monitor discussions around important topics or breaking news to identify and report on manipulation attempts:

```bash
# Monitor a specific post for bot activity
python -m src.monitor --post "https://www.instagram.com/p/EXAMPLE/"

# Review detected bots
python -m src.review_bots
```

### For Researchers & Academics
Study patterns of manipulation over time and contribute to improving detection methods:

```bash
# Add an account to monitor consistently
python -m src.add_account add "target_account"

# Monitor the account
python -m src.monitor --account "target_account"
```

### For Digital Rights Organizations
Document evidence of coordinated campaigns and advocate for platform accountability:

```bash
# Monitor multiple accounts
python -m src.add_account add "suspicious_account1"
python -m src.add_account add "suspicious_account2"

# Run automated monitoring
python -m src.monitor
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/OpenSocialMonitor/OpenSocialMonitor.git
   cd OpenSocialMonitor
   ```

2. **Set up a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up your environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Instagram credentials
   ```

5. **Initialize the database**
   ```bash
   python -m src.database.db_setup
   ```

## 📚 Usage Guide

### Monitoring Social Media

```bash
# Monitor a specific post
python -m src.monitor --post "https://www.instagram.com/p/EXAMPLE/"

# Monitor recent posts from an account
python -m src.monitor --account "target_account" --posts 3

# Monitor all tracked accounts
python -m src.monitor
```

### Managing Accounts to Monitor

```bash
# Add an account to monitor
python -m src.add_account add "target_account"

# List all monitored accounts
python -m src.add_account list

# Enable monitoring for an account
python -m src.add_account enable "target_account"

# Disable monitoring for an account
python -m src.add_account disable "target_account"
```

### Reviewing and Responding to Bots

```bash
# List pending bot warnings
python -m src.review_bots

# View details about a specific detection
python -m src.review_bots view 123

# Approve and send a warning comment
python -m src.review_bots approve 123
```

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

### Extending to New Platforms

The system is designed for easy platform expansion. To add support for a new platform:

1. Create a new connector in `src/platforms/`
2. Implement the required methods (see `instagram.py` for reference)
3. Update detection algorithms for platform-specific signals if needed

### Improving Detection Algorithms

Detection can always be enhanced:

1. Add new indicators in `src/detection/indicators.py`
2. Improve coordination detection with new patterns
3. Fine-tune thresholds and weights

### Adding Features

Some ideas for new features:

- Web interface for easier monitoring
- Report generation and visualization
- Historical trend analysis
- API for integration with other tools

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

## 🔮 Vision & Roadmap

### Short-term Goals
- Expand platform support to Twitter/X and Facebook
- Improve detection accuracy and effective usage of platform API's
- Build example datasets from real manipulation campaigns

### Medium-term Goals
- Create a web dashboard for easier monitoring
- Build a public database of manipulation patterns

### Long-term Vision
- Create an ecosystem of transparent tools for fighting misinformation
- Partner with journalists, researchers, and rights organizations
- Develop educational resources about detecting manipulation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Contact & Community

- GitHub Issues: For bug reports and feature requests
- [Join our community subreddit](https://reddit.com/r/OpenSocialMonitor) (coming soon)
