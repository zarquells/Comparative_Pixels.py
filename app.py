import streamlit as st
from pymongo import MongoClient
import gridfs
from PIL import Image
import io
import numpy as np
import io
import cv2

try:
    # Conexão com o MongoDB Atlas
    uri = "mongodb+srv://ericaljesus_db_user:rOCFjp2BUE76Qu8Q@clusteraulasrafael.xu0bcax.mongodb.net/?appName=ClusterAulasRafael"
    client = MongoClient(uri)
    db = client['midias']
    fs = gridfs.GridFS(db)
except Exception as e:
    st.warning(f'Algo deu errado ao conectar no banco de dados: {e}')

st.title("Projeto de Análise de Pixels")
st.write('Feito no curso de Inteligência e Análise de Dados - Senai Suíço-Brasileira')

# Buscar todos os arquivos armazenados no GridFS
arquivos = list(fs.find())

if not arquivos:
    st.warning("Nenhuma imagem encontrada no banco de dados nativo da aplicação. Tente novamente.")
else:
    st.divider()
    st.subheader('Comparação de imagens')
    st.text('Insira uma imagem para comparação com a base de dados nativa.')

    # Opções para entrada de imagem
    option = st.radio(
        "Escolha como deseja fornecer a imagem:",
        ["Foto de agora", "Como arquivo JPG/JPEG"],
        horizontal=True
    )

    user_image_input = None
    user_image = None

    if option == "Foto de agora":
        camera_photo = st.camera_input("Tire uma foto bem bonita!")

        if camera_photo is not None:
            user_image_input = camera_photo
            user_image = Image.open(camera_photo)
    elif option == "Como arquivo JPG/JPEG":
        uploaded_file = st.file_uploader(
            "Escolha um arquivo JPG/JPEG",
            type=["jpg", "jpeg"],
            accept_multiple_files=False
        )

        if uploaded_file is not None:
            user_image_input = uploaded_file
            user_image = Image.open(uploaded_file)

    if user_image_input is not None:
        user_image_input.seek(0)
        user_image_bytes = user_image_input.read()
        user_image_array = np.frombuffer(user_image_bytes, dtype=np.uint8)
        user_gray = cv2.imdecode(user_image_array, cv2.IMREAD_GRAYSCALE)

        user_image_path = "temp_user_image.jpg"
        arquivos = list(fs.find())

        progress_bar = st.progress(0)
        status_text = st.empty()

        melhor_similaridade = float('inf')
        melhor_imagem = None
        melhor_filename = None
        melhor_dados = None
        erros_encontrados = []
        comparacoes_realizadas = 0

        if user_gray is None:
            st.warning("Falha ao decodificar a imagem de entrada. A comparação não pode prosseguir.")

        try:
            target_size = (128, 128)
            user_resized = cv2.resize(user_gray, target_size)

        except Exception as e:
            st.warning(f"Erro ao redimensionar imagem para comparação: {e}")


        # Comparar com cada imagem do banco
        for idx, arquivo in enumerate(arquivos):
            try:
                # Atualizar progresso
                progress = (idx + 1) / len(arquivos)
                progress_bar.progress(progress)
                status_text.text(f"Processando imagem {idx + 1}/{len(arquivos)}: {arquivo.filename}")

                # Ler imagem do GridFS
                dados = arquivo.read()

                # Verificar se os dados foram lidos corretamente
                if dados is None or len(dados) == 0:
                    erros_encontrados.append(f"Imagem {arquivo.filename}: dados vazios")
                    continue

                imagem_array = np.frombuffer(dados, dtype=np.uint8)
                db_gray = cv2.imdecode(imagem_array, cv2.IMREAD_GRAYSCALE)

                try:
                    db_resized = cv2.resize(db_gray, target_size)
                    distancia = np.sum(abs(user_resized.astype("float") - db_resized.astype("float")))

                    comparacoes_realizadas += 1

                    if distancia < melhor_similaridade:
                        melhor_similaridade = distancia
                        melhor_imagem = db_gray
                        melhor_filename = arquivo.filename
                        melhor_dados = dados

                except Exception as e:
                    st.warning(f'Algo deu errado ao comparar: {e}')
                    continue

            except Exception as e:
                st.warning(f'Algo deu errado ao converter: {e}')
                continue

            progress_bar.empty()
            status_text.empty()

        st.divider()            
        st.info(f"Comparações realizadas com sucesso: {comparacoes_realizadas} de {len(arquivos)} imagens")

        # Exibir resultado
        if melhor_imagem is not None:            
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Sua Imagem")
                st.image(user_image, use_container_width=True)

            with col2:
                st.subheader("Imagem Mais Similar")
                st.image(melhor_imagem, caption=f"{melhor_filename}", use_container_width=True)

        else:
            st.error("Não foi possível encontrar uma imagem similar. Tente com outra imagem.")
    else:
        st.warning('Nenhuma imagem fornecida para comparação.')

    st.divider()
    st.info('Veja mais detalhes das imagens no banco de dados abaixo!')
    st.write(f"Total de imagens armazenadas: {len(arquivos)}")

    # Exibir imagens em colunas
    cols = st.columns(3)  # 3 imagens por linha
    for i, arquivo in enumerate(arquivos):
        # dados = arquivo.read()
        # imagem = Image.open(io.BytesIO(dados))
        arquivo_cursor = fs.get(arquivo._id)
        dados = arquivo_cursor.read() 
        imagem = Image.open(io.BytesIO(dados))

        with cols[i % 3]:
            st.image(imagem, caption=arquivo.filename, use_container_width=True)
            st.download_button(
                label="Baixar",
                data=dados,
                file_name=arquivo.filename,
                mime="image/jpeg"
            )