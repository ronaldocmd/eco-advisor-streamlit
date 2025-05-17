import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_page():
    st.set_page_config(
        page_title='EcoAdvisor - Assistente Sustentável',
        page_icon='🌿',
        layout='wide',
        initial_sidebar_state='auto'
    )

def configure_gemini_api():
    try:
        api_key = os.environ.get('STREAMLIT_GOOGLE_API_KEY') # Lembre-se de usar este nome para o Secret no Streamlit Cloud
        if not api_key:
            logging.error('Variável de ambiente STREAMLIT_GOOGLE_API_KEY não encontrada ou vazia.')
            st.error('🚫 Chave da API do Google não configurada corretamente para a aplicação.')
            st.info('Verifique a configuração dos Secrets no Streamlit Community Cloud.') # Ajustado para o contexto do deploy
            return False
        genai.configure(api_key=api_key)
        logging.info('API do Google Gemini configurada com sucesso via variável de ambiente.')
        return True
    except Exception as e:
        logging.error(f'Erro ao configurar a API do Google Gemini: {e}')
        handle_error('Falha ao configurar a API do Google Gemini.', e)
        return False

def get_environmental_analysis(image_bytes: bytes, custom_prompt: str) -> str | None:
    if not image_bytes:
        logging.warning('Tentativa de análise sem imagem.')
        st.warning('⚠️ Por favor, envie uma imagem primeiro.')
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes))
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content([custom_prompt, img], stream=False)
        response.resolve()
        return response.text
    except genai.types.generation_types.BlockedPromptException as bpe:
        logging.error(f'API Gemini bloqueou o prompt ou a imagem: {bpe}')
        handle_error('🚫 A API bloqueou a análise.', bpe)
        return None
    except genai.types.generation_types.StopCandidateException as sce:
        logging.error(f'API Gemini interrompeu a geração: {sce}')
        handle_error('⚠️ A API interrompeu a geração da resposta.', sce)
        if sce.candidates and sce.candidates[0].content.parts:
            return ''.join(part.text for part in sce.candidates[0].content.parts if hasattr(part, 'text'))
        return 'A geração da resposta foi interrompida pela API.'
    except Exception as e:
        logging.error(f'Erro com API Gemini: {e}')
        handle_error(f'Ocorreu um erro com a API Gemini: {e}', e)
        return None

def display_initial_interface():
    st.title('🌿 EcoAdvisor: Seu Assistente de Decisões Sustentáveis')
    st.subheader('Envie uma foto da embalagem ou rótulo do produto para uma análise ambiental.')
    st.markdown('---')
    if not os.environ.get('STREAMLIT_GOOGLE_API_KEY'):
        st.warning('🔑 **Atenção:** API Key do Google não parece estar configurada.')
    return st.file_uploader('Escolha uma imagem...', type=['jpg', 'jpeg', 'png'], help='Formatos: JPG, JPEG, PNG.')

def display_analysis_results(analysis_text: str):
    st.markdown('---')
    st.subheader('🔬 Resultados da Análise Ambiental:')
    if not analysis_text or not analysis_text.strip():
        st.warning('⚠️ A análise não retornou conteúdo.')
        return

    sections = {
        '1. Descrição geral do produto.': '📝 **Descrição Geral do Produto**',
        '2. Materiais identificáveis na embalagem.': '♻️ **Materiais da Embalagem**',
        '3. Estimativa aproximada da pegada de carbono (em kg CO2).': '💨 **Pegada de Carbono Estimada**',
        '4. Instruções de descarte correto no Brasil.': '🗑️ **Descarte Correto (Brasil)**',
        '5. Sugestões de alternativas ecológicas disponíveis no mercado nacional.': '💡 **Alternativas Ecológicas**'
    }
    current_section_content = []
    current_section_title = 'ℹ️ **Informações Adicionais**'

    with st.expander('Ver análise detalhada', expanded=True):
        s = analysis_text
        # Converte a string literal '\\n' (duas barras) para o caractere newline '\n'
        s = s.replace('\\\\n', '\n')
        # Converte a string literal '\n' (uma barra) para o caractere newline '\n'
        # Esta segunda substituição é importante caso a primeira não tenha pego todas as variações
        # ou se a API retornar '\n' literal diretamente.
        s = s.replace('\\n', '\n')
        lines = s.split('\n')

        found_section = False
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue
            matched_key = None
            for key_prompt, title_display in sections.items():
                if line_strip.startswith(key_prompt.split('.')[0] + '.'):
                    if current_section_content:
                        st.markdown(f'### {current_section_title}')
                        st.markdown('\n'.join(current_section_content).strip())
                        current_section_content = []
                    current_section_title = title_display
                    line_content = line_strip.split('.', 1)[-1].strip() if '.' in line_strip else line_strip
                    if line_content:
                        current_section_content.append(line_content)
                    matched_key = True
                    found_section = True
                    break
            if not matched_key:
                current_section_content.append(line_strip)
        if current_section_content:
            st.markdown(f'### {current_section_title}')
            st.markdown('\n'.join(current_section_content).strip())
        elif not found_section and analysis_text.strip():
            st.markdown(s) # 's' já foi processado para ter newlines corretos

def handle_error(user_message: str, error_details: Exception = None):
    st.error(f'😕 Ops! {user_message}')
    if error_details:
        logging.error(f'Detalhes do erro: {error_details}', exc_info=True)
    st.markdown('---')
    st.info('💡 Dica: Verifique sua conexão, imagem, API Key ou tente novamente.')

def main():
    setup_page()
    if not configure_gemini_api():
        st.markdown('## 🚧 Aplicação em modo limitado 🚧')
        st.markdown('API Key do Google não configurada corretamente.')
        st.stop()

    uploaded_file = display_initial_interface()
    if uploaded_file is not None:
        st.image(uploaded_file, caption='🖼️ Imagem Enviada', width=400) # Largura da imagem ajustada
        st.markdown('---')
        if st.button('🔍 Analisar Imagem', use_container_width=True, type='primary'):
            with st.spinner('🌍 Analisando a imagem...'):
                try:
                    image_bytes = uploaded_file.getvalue()
                    # Para o prompt, \\n é necessário para que a API Gemini receba \n literal
                    gemini_prompt = (
                        'Você é um especialista em sustentabilidade e análise ambiental. ' +
                        'Analise a embalagem enviada e forneça:\\n' +
                        '1. Descrição geral do produto.\\n' +
                        '2. Materiais identificáveis na embalagem.\\n' +
                        '3. Estimativa aproximada da pegada de carbono (em kg CO2).\\n' +
                        '4. Instruções de descarte correto no Brasil.\\n' +
                        '5. Sugestões de alternativas ecológicas disponíveis no mercado nacional.\\n' +
                        'Seja didático, direto e objetivo. Formate cada item com seu número correspondente e inicie cada item em uma nova linha.'
                    )
                    analysis_result = get_environmental_analysis(image_bytes, gemini_prompt)
                    if analysis_result:
                        display_analysis_results(analysis_result)
                    else:
                        st.info('Não foi possível obter a análise. Verifique as mensagens acima.')
                except Exception as e:
                    handle_error('Erro inesperado no processamento.', e)
    else:
        st.markdown('---')
        col1, col2, col3 = st.columns(3)
        with col1: st.info('🌱 **Passo 1:** Prepare a imagem.')
        with col2: st.info('📤 **Passo 2:** Faça o upload.')
        with col3: st.info('📊 **Passo 3:** Clique em \'Analisar\'.') # Aspa simples escapada
        st.markdown('<br>', unsafe_allow_html=True)
        st.success('Prontos para decisões mais sustentáveis! 🌍✨')

if __name__ == '__main__':
    main()