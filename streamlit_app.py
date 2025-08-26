import streamlit as st
import os
import sys
import subprocess
from pathlib import Path
import time

# audio_extractor.py의 AudioExtractor 클래스를 직접 가져오기
# Streamlit 환경에서 moviepy.editor가 아닌 moviepy.video.io.VideoFileClip에서 VideoFileClip을 가져오도록 수정
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip
    except ImportError:
        VideoFileClip = None

from pydub import AudioSegment


class AudioExtractor:
    """영상에서 오디오를 추출하는 클래스"""
    
    def __init__(self):
        self.supported_video_formats = [
            ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"
        ]
        self.supported_audio_formats = [".mp3", ".flac", ".wav", ".aac", ".ogg"]
    
    def validate_input_file(self, input_path):
        """입력 파일 유효성 검사"""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"입력 파일을 찾을 수 없습니다: {input_path}")
        
        file_ext = Path(input_path).suffix.lower()
        if file_ext not in self.supported_video_formats:
            raise ValueError(f"지원하지 않는 비디오 형식입니다: {file_ext}")
        
        return True
    
    def validate_output_format(self, output_path):
        """출력 형식 유효성 검사"""
        file_ext = Path(output_path).suffix.lower()
        if file_ext not in self.supported_audio_formats:
            raise ValueError(f"지원하지 않는 오디오 형식입니다: {file_ext}")
        
        return file_ext
    
    def extract_audio_with_ffmpeg(self, input_path, output_path, format_type):
        """
        ffmpeg을 직접 사용하여 오디오 추출 (최고 품질 유지)
        """
        try:
            if format_type == ".mp3":
                # MP3: 최고 품질 설정 (320kbps)
                cmd = [
                    "ffmpeg",
                    "-i",
                    input_path,
                    "-vn",  # 비디오 스트림 제거
                    "-acodec",
                    "libmp3lame",
                    "-ab",
                    "320k",  # 320kbps 비트레이트
                    "-ar",
                    "44100",  # 44.1kHz 샘플레이트
                    "-ac",
                    "2",  # 스테레오
                    "-y",  # 덮어쓰기 허용
                    output_path,
                ]
            elif format_type == ".flac":
                # FLAC: 무손실 압축
                cmd = [
                    "ffmpeg",
                    "-i",
                    input_path,
                    "-vn",  # 비디오 스트림 제거
                    "-acodec",
                    "flac",
                    "-compression_level",
                    "8",  # 최고 압축 레벨
                    "-y",  # 덮어쓰기 허용
                    output_path,
                ]
            elif format_type == ".wav":
                # WAV: 무손실 원본
                cmd = [
                    "ffmpeg",
                    "-i",
                    input_path,
                    "-vn",  # 비디오 스트림 제거
                    "-acodec",
                    "pcm_s16le",  # 16비트 PCM
                    "-y",  # 덮어쓰기 허용
                    output_path,
                ]
            else:
                # 기타 형식: 원본 코덱 복사 시도
                cmd = [
                    "ffmpeg",
                    "-i",
                    input_path,
                    "-vn",  # 비디오 스트림 제거
                    "-acodec",
                    "copy",  # 원본 오디오 코덱 복사
                    "-y",  # 덮어쓰기 허용
                    output_path,
                ]
            
            st.session_state.log_messages.append(f"ffmpeg 명령어 실행: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                st.session_state.log_messages.append(f"ffmpeg 오류: {result.stderr}")
                return False
            
            st.session_state.log_messages.append(f"오디오 추출 완료: {output_path}")
            return True
            
        except Exception as e:
            st.session_state.log_messages.append(f"ffmpeg 추출 중 오류 발생: {e}")
            return False
    
    def extract_audio_with_moviepy(self, input_path, output_path):
        """
        MoviePy를 사용하여 오디오 추출 (백업 방법)
        """
        try:
            st.session_state.log_messages.append("MoviePy를 사용하여 오디오 추출 중...")
            video = VideoFileClip(input_path)
            audio = video.audio
            
            # 임시 WAV 파일로 추출
            temp_wav = output_path.replace(Path(output_path).suffix, "_temp.wav")
            audio.write_audiofile(temp_wav, verbose=False, logger=None)
            
            # 원하는 형식으로 변환
            if not output_path.endswith(".wav"):
                self.convert_audio_format(temp_wav, output_path)
                os.remove(temp_wav)  # 임시 파일 삭제
            else:
                os.rename(temp_wav, output_path)
            
            video.close()
            audio.close()
            
            st.session_state.log_messages.append(f"MoviePy로 오디오 추출 완료: {output_path}")
            return True
            
        except Exception as e:
            st.session_state.log_messages.append(f"MoviePy 추출 중 오류 발생: {e}")
            return False
    
    def convert_audio_format(self, input_audio_path, output_path):
        """
        pydub을 사용하여 오디오 형식 변환
        """
        try:
            audio = AudioSegment.from_wav(input_audio_path)
            
            output_format = Path(output_path).suffix[1:]  # 확장자에서 점 제거
            
            if output_format == "mp3":
                audio.export(output_path, format="mp3", bitrate="320k")
            elif output_format == "flac":
                audio.export(output_path, format="flac")
            else:
                audio.export(output_path, format=output_format)
            
            return True
            
        except Exception as e:
            st.session_state.log_messages.append(f"오디오 형식 변환 중 오류 발생: {e}")
            return False
    
    def get_audio_info(self, file_path):
        """
        오디오 파일 정보 조회
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                
                info = json.loads(result.stdout)
                
                for stream in info.get("streams", []):
                    if stream.get("codec_type") == "audio":
                        return {
                            "codec": stream.get("codec_name"),
                            "sample_rate": stream.get("sample_rate"),
                            "channels": stream.get("channels"),
                            "bit_rate": stream.get("bit_rate"),
                            "duration": float(stream.get("duration", 0)),
                        }
            
            return None
            
        except Exception as e:
            st.session_state.log_messages.append(f"오디오 정보 조회 중 오류 발생: {e}")
            return None
    
    def extract_audio(self, input_path, output_path):
        """
        메인 오디오 추출 함수
        """
        try:
            # 입력 파일 검증
            self.validate_input_file(input_path)
            
            # 출력 형식 검증
            output_format = self.validate_output_format(output_path)
            
            # 출력 디렉토리 생성
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            st.session_state.log_messages.append(f"입력 파일: {input_path}")
            st.session_state.log_messages.append(f"출력 파일: {output_path}")
            st.session_state.log_messages.append(f"출력 형식: {output_format}")

            # 원본 비디오 정보 출력
            video_info = self.get_audio_info(input_path)
            if video_info:
                st.session_state.log_messages.append("원본 오디오 정보:")
                st.session_state.log_messages.append(f"  코덱: {video_info.get('codec', 'Unknown')}")
                st.session_state.log_messages.append(f"  샘플레이트: {video_info.get('sample_rate', 'Unknown')} Hz")
                st.session_state.log_messages.append(f"  채널: {video_info.get('channels', 'Unknown')}")
                st.session_state.log_messages.append(f"  비트레이트: {video_info.get('bit_rate', 'Unknown')} bps")
                st.session_state.log_messages.append(f"  길이: {video_info.get('duration', 0):.2f} 초")
            # ffmpeg을 우선적으로 사용
            success = self.extract_audio_with_ffmpeg(
                input_path, output_path, output_format
            )
            
            # ffmpeg 실패 시 MoviePy 사용
            if not success:
                st.session_state.log_messages.append("ffmpeg 추출 실패, MoviePy로 재시도...")
                success = self.extract_audio_with_moviepy(input_path, output_path)
            
            if success and os.path.exists(output_path):
                # 추출된 오디오 정보 출력
                extracted_info = self.get_audio_info(output_path)
                if extracted_info:
                    st.session_state.log_messages.append("추출된 오디오 정보:")
                    st.session_state.log_messages.append(f"  코덱: {extracted_info.get('codec', 'Unknown')}")
                    st.session_state.log_messages.append(f"  샘플레이트: {extracted_info.get('sample_rate', 'Unknown')} Hz")
                    st.session_state.log_messages.append(f"  채널: {extracted_info.get('channels', 'Unknown')}")
                    st.session_state.log_messages.append(f"  비트레이트: {extracted_info.get('bit_rate', 'Unknown')} bps")
                    st.session_state.log_messages.append(f"  길이: {extracted_info.get('duration', 0):.2f} 초")
                
                file_size = os.path.getsize(output_path)
                st.session_state.log_messages.append(
                    f"파일 크기: {file_size / (1024*1024):.2f} MB"
                )
                st.session_state.log_messages.append("오디오 추출이 성공적으로 완료되었습니다!")
                return True
            else:
                st.session_state.log_messages.append("오디오 추출에 실패했습니다.")
                return False
        
        except Exception as e:
            st.session_state.log_messages.append(f"오류 발생: {e}")
            return False


# Streamlit 앱 시작
st.set_page_config(page_title="영상 오디오 추출기", layout="centered")
st.title("🎥 영상 오디오 추출기")
st.markdown("영상 파일에서 오디오를 MP3, FLAC 등 다양한 형식으로 추출합니다.")

# 세션 상태 초기화
if "log_messages" not in st.session_state:
    st.session_state.log_messages = []
if "output_audio_path" not in st.session_state:
    st.session_state.output_audio_path = None

# 파일 업로드
uploaded_file = st.file_uploader("비디오 파일 선택", type=["mp4", "avi", "mkv", "mov", "wmv", "flv", "webm", "m4v"])

# 출력 형식 선택
output_format = st.selectbox(
    "출력 오디오 형식 선택",
    ("mp3", "flac", "wav", "aac", "ogg"),
    index=0,  # 기본값 mp3
)

# 추출 버튼
if st.button("오디오 추출 시작"): 
    if uploaded_file is not None:
        st.session_state.log_messages = [] # 로그 초기화
        st.session_state.output_audio_path = None
        
        # 임시 파일로 저장
        input_video_path = os.path.join("/tmp", uploaded_file.name)
        with open(input_video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # 출력 파일 경로 설정
        output_audio_name = Path(uploaded_file.name).stem + f".{output_format}"
        output_audio_path = os.path.join("/tmp", output_audio_name)
        
        extractor = AudioExtractor()
        
        with st.spinner("오디오 추출 중... 잠시만 기다려 주세요."):
            success = extractor.extract_audio(input_video_path, output_audio_path)
            
            if success:
                st.success("오디오 추출이 완료되었습니다!")
                st.session_state.output_audio_path = output_audio_path
            else:
                st.error("오디오 추출에 실패했습니다. 로그를 확인해주세요.")
        
        # 임시 입력 파일 삭제
        if os.path.exists(input_video_path):
            os.remove(input_video_path)
            st.session_state.log_messages.append(f"임시 입력 파일 삭제: {input_video_path}")
    else:
        st.warning("비디오 파일을 먼저 업로드해주세요.")

# 추출된 오디오 파일 다운로드 링크
if st.session_state.output_audio_path and os.path.exists(st.session_state.output_audio_path):
    with open(st.session_state.output_audio_path, "rb") as f:
        st.download_button(
            label="오디오 파일 다운로드",
            data=f.read(),
            file_name=Path(st.session_state.output_audio_path).name,
            mime=f"audio/{output_format}"
        )
    # 다운로드 후 임시 출력 파일 삭제
    os.remove(st.session_state.output_audio_path)
    st.session_state.log_messages.append(f"임시 출력 파일 삭제: {st.session_state.output_audio_path}")
    st.session_state.output_audio_path = None # 상태 초기화

# 로그 메시지 표시
st.subheader("로그")
log_container = st.empty()
with log_container.container():
    for message in st.session_state.log_messages:
        st.code(message, language="text")

# Streamlit 앱 실행 방법 안내
st.markdown("""
--- 
### 사용 방법
1. 위에 비디오 파일을 업로드하세요.
2. 원하는 출력 오디오 형식을 선택하세요.
3. '오디오 추출 시작' 버튼을 클릭하세요.
4. 추출이 완료되면 오디오 파일을 다운로드할 수 있습니다.
""")

# Streamlit 앱 실행 안내 (개발 환경용)
# if __name__ == "__main__":
#     st.write("이 앱은 Streamlit으로 실행되어야 합니다. 터미널에서 다음 명령어를 실행하세요:")
#     st.code("streamlit run streamlit_app.py")


