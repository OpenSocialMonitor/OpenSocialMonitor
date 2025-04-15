---
layout: default
title: OpenSocialMonitor - Detecting Social Media Manipulation
---

# OpenSocialMonitor

## Empowering Communities to Combat Social Media Manipulation

Social media has become central to our information ecosystem, but it's increasingly manipulated by automated accounts and coordinated campaigns. These manipulations distort public discourse, spread misinformation, and create artificial consensus that influences real people.

**OpenSocialMonitor** gives communities the power to detect and expose this manipulation.

### Why This Tool Exists

Commercial platforms often lack incentives to fully address manipulation, as engagement—even artificial engagement—drives their business models. We believe:

- People deserve to know when they're being manipulated
- Communities should have tools to protect their own discourse
- Transparency is essential for informed decision-making
- Detection technology should be open and community-driven

Our tool is politically neutral. We support everyone's right to form and express their opinions, but believe those opinions should be formed based on authentic information—not manipulation by automated networks.

## How It Works

OpenSocialMonitor uses behavioral and linguistic markers to identify potential bot accounts and detect coordination between accounts spreading identical content. When potential manipulation is detected, users can issue warning comments to alert others.

## Get Started

### Installation

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

   **Important:** We strongly recommend using a dedicated account for monitoring, not your personal account.

5. **Initialize the database**
   ```bash
   python -m src.database.db_setup
   ```

### Basic Usage

#### Monitor an Account

If you notice suspicious activity from a particular account:

```bash
# Add the account to your monitoring list
python -m src.add_account add "account_name"

# Monitor their recent posts
python -m src.monitor --account "account_name"
```

#### Analyze a Specific Post

If you encounter a post with suspicious engagement patterns:

```bash
# Analyze the post for bot activity
python -m src.monitor --post "https://www.instagram.com/p/EXAMPLE/"
```

#### Review Bot Detections

After monitoring, review potential bots that were detected:

```bash
# List all pending bot warnings
python -m src.review_bots

# View details about a specific detection
python -m src.review_bots view 123

# Approve and send a warning comment
python -m src.review_bots approve 123
```

## Safety and Ethics

- **Avoid harassment**: Use the tool to provide information, not to target individuals
- **Be transparent**: When posting warnings, make it clear they're based on automated detection
- **Consider context**: Not all bot-like behavior comes from actual bots
- **Protect yourself**: Be aware that excessive API usage may lead to account limitations

## Join Our Community

We're building a community of people committed to transparent, authentic communication online. Here's how you can get involved:

- **Use the tool** and provide feedback through GitHub Issues
- **Contribute code** to improve detection algorithms or add new features
- **Help with documentation** to make the project more accessible
- **Spread the word** about the importance of detecting manipulation

Check our [Contributing Guide](https://github.com/OpenSocialMonitor/OpenSocialMonitor/blob/main/CONTRIBUTING.md) for more information on how to participate.

## A Note from the Maintainer

I created OpenSocialMonitor because I believe communities should have the tools to protect their own discourse. While my coding skills are developing, I'm committed to maintaining this project and welcome contributions from those with technical expertise.

I review pull requests weekly (typically on weekends) and am actively seeking co-maintainers to help the project reach its full potential.

Together, we can make social media more transparent and resistant to manipulation.

## Contact & Resources

- [GitHub Repository](https://github.com/OpenSocialMonitor/OpenSocialMonitor)
- [Report Issues](https://github.com/OpenSocialMonitor/OpenSocialMonitor/issues)
- [Community Subreddit](https://reddit.com/r/OpenSocialMonitor) (coming soon)
