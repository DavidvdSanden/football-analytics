# 🗺️ Project Roadmap


## 🎯 Goal
Develop skills in:
- ⚽ xG modeling
- 📊 Player evaluation (expected threat–based)
- 🗃️ Data handling & pipelines
- 🎨 Front-end visualization
- 🧠 Team tactics
- 🏥 Injury prediction

<br>

## 🚧 Current Status

#### ✅ Data & Infrastructure
- [x] Data collection
- [x] Database creation
- [x] Data augmentation
- [x] Feature engineering (distance, angle, body part)

#### 🤖 Modeling
- [x] Baseline logistic regression
- [x] Neural network xG model

#### 📈 Analysis
- [ ] Expected Threat (xT)
- [ ] Player evaluation
- [ ] Team tactics

#### 🎨 Front End
- [x] Visualization (Streamlit or similar)

#### 💰 External Data
- [ ] Transfer value scraping

<br>

## 🧩 Next Milestones

**Milestone 1 – Data Enrichment**
- Save all events (passes, dribbles, tackles, etc.) to DB for later usage in xT/xV model

**Milestone 2 – Player Value**
- xT model
- Player contribution metrics
- Transfermarket scraping
- Create model that compares value across / within matches and leagues

**Milestone 3 – Team Characteristics**
- Define playing style
- Recommended strategy / style
- Identify combinations

<br>

## 💡 Ideas / Backlog
- Cross-league comparisons
- League-specific priors
- Position-aware models
- Injury risk estimation
- Items that add value for players (xV):
   - Shoot (xG)
   - Pass / dribble to more valuable situation
   - Win 50/50
   - Regain possession (prevent xG from opponent + create own xG) -> can be on ground and via air
   - Prevent possession of opponent in more valuable xT
   - Create valuable option for other player to move possession to
- Find data that has freeze_frames for all events (close to live tracking)

<br>

## ❓ Open Questions
- Team-specific xG calibration
