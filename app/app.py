import streamlit as st
import pandas as pd
import numpy as np
import h5py
import os
from pathlib import Path

@st.cache_data
def download_h5():
    """
    HDF5 dosyasını Hugging Face veya başka bir kaynaktan indirip döndürür.
    Eğer dosya zaten mevcutsa, mevcut olanı döndürür.
    """
    h5_path = Path("game_recommendation.h5")

    # Eğer dosya zaten varsa, yeniden indirmeye gerek yok
    if h5_path.exists():
        return h5_path

    # Hugging Face veya başka bir kaynaktan indir
    hf_url = "https://huggingface.co/datasets/Tunahanyrd/steam-game-recommendation/resolve/main/models/game_recommendation.h5"
    try:
        import requests
        with requests.get(hf_url, stream=True) as r:
            r.raise_for_status()
            with open(h5_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return h5_path
    except Exception as e:
        st.error(f"🚨 HDF5 dosyası indirilemedi: {e}")
        return None


@st.cache_data
def load_hdf5():
    try:
        h5_path = download_h5()
        if h5_path is None:
            return None, None

        with h5py.File(h5_path, "r") as file:
            # DataFrame oluştur
            df_dict = {col: file[col][:] for col in file.keys() if col != "similarity_matrix"}
            df = pd.DataFrame(df_dict)

            # NumPy array olarak saklanması gereken sütunlar
            vector_columns = [
                "developers_vector", "publishers_vector", "category_vector", 
                "genre_vector", "tags_matrix", "tags_tfidf_matrix", 
                "feature_matrix", "final_feature_vectors", "short_desc_matrix"
            ]

            # Eğer sütun list tipindeyse NumPy array'e çevir
            for col in vector_columns:
                if col in df.columns and isinstance(df[col].iloc[0], list):
                    df[col] = df[col].apply(np.array)

            # Benzerlik matrisini yükle
            similarity_matrix = file["similarity_matrix"][:]

        return df, similarity_matrix

    except Exception as e:
        st.error(f"⚠️ Data importing error: {e}")
        return None, None


def recommend_games(game_id, top_n=10, min_similarity=0.5):
    """
    Suggests similar games for the specified `game_id`.
    
    Args:
        game_id (int): Steam App ID.
        top_n (int): Number of recommendation
        min_similarity (float)
        
    """
    if game_id not in df["app_id"].values:
        st.error("⚠️ Recommendations for this game cannot be calculated. Please try another game.!")
        return None

    app_id_to_index = {app_id: i for i, app_id in enumerate(df["app_id"].values)}

    target_idx = app_id_to_index.get(game_id, None)
    
    if target_idx is None:
        st.error("⚠️ Invalid game ID!")
        return None

    if target_idx >= similarity_matrix.shape[0]:
        st.error("⚠️ Recommendations for this game cannot be calculated. Please try another game.")
        return None

    sim_scores = list(enumerate(similarity_matrix[target_idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

    recommendations = []
    for idx, score in sim_scores[1:]:  
        if score >= min_similarity:
            recommendations.append((df.iloc[idx]["app_id"], df.iloc[idx]["name"], score))
        if len(recommendations) >= top_n:
            break

    return recommendations


st.title("🎮 Game Recommendation")
st.markdown("**Enter your game Steam ID and see similar games!**")

game_id = st.text_input("Enter your game Steam ID:", "")

if st.button("Get Recommendation"):
    if game_id.isdigit():
        game_id = int(game_id)
        recommendations = recommend_games(game_id)

        if recommendations:
            st.markdown("### 📌 Recommended Games:")
            for app_id, name, similarity in recommendations:
                st.markdown(f"🔹 **{name}** (Similarity: {similarity:.3f})")
        else:
            st.error("ID is not found.")
    else:
        st.warning("Please enter a valid ID.!")
