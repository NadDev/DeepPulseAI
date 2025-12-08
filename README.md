# Gestionnaire de Portfolio de Cryptomonnaies

Application web complète pour gérer et suivre votre portfolio de cryptomonnaies en temps réel.

## 🚀 Fonctionnalités

- **Dashboard interactif** avec statistiques en temps réel
- **Suivi de portfolio** avec calcul automatique des profits/pertes
- **Liste des marchés** avec les 50 principales cryptomonnaies
- **Graphiques de prix** interactifs avec périodes personnalisables
- **Recherche de cryptomonnaies** pour ajouter à votre portfolio
- **Interface responsive** adaptée mobile et desktop
- **API CoinGecko** pour les données en temps réel

## 📋 Prérequis

- Python 3.8 ou supérieur
- Node.js 16 ou supérieur
- npm ou yarn

## 🛠️ Installation

### Backend (Python/Flask)

1. Naviguez vers le dossier backend :
```bash
cd backend
```

2. Créez un environnement virtuel Python :
```bash
python -m venv venv
```

3. Activez l'environnement virtuel :
- Windows :
  ```bash
  venv\Scripts\activate
  ```
- Linux/Mac :
  ```bash
  source venv/bin/activate
  ```

4. Installez les dépendances :
```bash
pip install -r requirements.txt
```

5. Copiez le fichier de configuration :
```bash
cp .env.example .env
```

6. Lancez le serveur backend :
```bash
python app.py
```

Le serveur backend sera accessible sur `http://localhost:5000`

### Frontend (React/Vite)

1. Ouvrez un nouveau terminal et naviguez vers le dossier frontend :
```bash
cd frontend
```

2. Installez les dépendances :
```bash
npm install
```

3. Lancez le serveur de développement :
```bash
npm run dev
```

Le frontend sera accessible sur `http://localhost:3000`

## 🎯 Utilisation

1. Ouvrez votre navigateur à l'adresse `http://localhost:3000`
2. Explorez le **Dashboard** pour voir les statistiques globales
3. Consultez les **Marchés** pour découvrir les cryptomonnaies disponibles
4. Accédez à **Mon Portfolio** pour gérer vos investissements :
   - Cliquez sur "Ajouter une crypto"
   - Recherchez la cryptomonnaie souhaitée
   - Entrez la quantité et le prix d'achat
   - Validez pour l'ajouter à votre portfolio

## 📁 Structure du Projet

```
CRBot/
├── backend/                 # Serveur Python Flask
│   ├── app.py              # Application principale
│   ├── requirements.txt    # Dépendances Python
│   └── .env.example        # Configuration exemple
│
├── frontend/               # Application React
│   ├── src/
│   │   ├── components/     # Composants React
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Portfolio.jsx
│   │   │   ├── CryptoList.jsx
│   │   │   └── CryptoDetail.jsx
│   │   ├── services/       # Services API
│   │   │   └── api.js
│   │   ├── App.jsx         # Composant principal
│   │   └── main.jsx        # Point d'entrée
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

## 🔌 API Endpoints

### Backend API

- `GET /api/health` - Vérification de l'état du serveur
- `GET /api/crypto/prices` - Liste des prix des cryptomonnaies
- `GET /api/crypto/search?q={query}` - Recherche de cryptomonnaies
- `GET /api/crypto/{coin_id}` - Détails d'une cryptomonnaie
- `GET /api/crypto/{coin_id}/chart?days={days}` - Données historiques
- `GET /api/portfolio` - Obtenir le portfolio
- `POST /api/portfolio` - Ajouter au portfolio
- `PUT /api/portfolio/{item_id}` - Modifier un élément
- `DELETE /api/portfolio/{item_id}` - Supprimer un élément

## 🎨 Technologies Utilisées

### Frontend
- React 18
- React Router pour la navigation
- Axios pour les requêtes HTTP
- Recharts pour les graphiques
- Lucide React pour les icônes
- Vite comme bundler

### Backend
- Flask (framework web Python)
- Flask-CORS pour la gestion CORS
- Requests pour les appels API externes
- CoinGecko API pour les données crypto

## 📝 Notes

- Les données du portfolio sont actuellement stockées en mémoire. Pour une application en production, utilisez une base de données (PostgreSQL, MongoDB, etc.)
- L'API CoinGecko gratuite a des limites de taux. Pour un usage intensif, envisagez un compte premium
- Les fichiers `.env` ne doivent jamais être commitées dans Git

## 🔐 Sécurité

Pour un déploiement en production :
- Ajoutez une authentification utilisateur
- Utilisez HTTPS
- Implémentez des limites de taux
- Utilisez une vraie base de données
- Ajoutez des variables d'environnement sécurisées
- Validez toutes les entrées utilisateur

## 📄 Licence

Ce projet est open source et disponible sous la licence MIT.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📧 Support

Pour toute question ou problème, n'hésitez pas à ouvrir une issue sur le dépôt GitHub.

---

Développé avec ❤️ pour la communauté crypto
