use crate::utils::logger;
use image::RgbaImage;
use screenshots::Screen;

#[derive(Clone)]
pub struct CapturedScreen {
    pub image: RgbaImage,
    pub origin_x: i32,
    pub origin_y: i32,
    pub method: &'static str,
}

pub fn capture_primary_screen() -> Result<CapturedScreen, String> {
    let screen = Screen::all()
        .map_err(|e| e.to_string())?
        .into_iter()
        .find(|screen| screen.display_info.is_primary)
        .ok_or("No primary screen found")?;

    capture_with_fallback(screen)
}

pub fn capture_screen_containing_point(x: i32, y: i32) -> Result<CapturedScreen, String> {
    let screen = Screen::from_point(x, y).map_err(|e| e.to_string())?;

    capture_with_fallback(screen)
}

pub fn crop_global(
    capture: &CapturedScreen,
    x: i32,
    y: i32,
    width: u32,
    height: u32,
) -> Result<RgbaImage, String> {
    let local_x = x - capture.origin_x;
    let local_y = y - capture.origin_y;
    let local_x = local_x.max(0) as u32;
    let local_y = local_y.max(0) as u32;
    let width = width.min(capture.image.width().saturating_sub(local_x));
    let height = height.min(capture.image.height().saturating_sub(local_y));

    if width == 0 || height == 0 {
        return Err("Invalid capture region dimensions".to_string());
    }

    Ok(image::DynamicImage::ImageRgba8(capture.image.clone())
        .crop_imm(local_x, local_y, width, height)
        .to_rgba8())
}

fn capture_with_fallback(screen: Screen) -> Result<CapturedScreen, String> {
    let origin_x = screen.display_info.x;
    let origin_y = screen.display_info.y;
    let image = screen.capture().map_err(|e| e.to_string())?;
    let black_ratio = dark_pixel_ratio(&image);

    logger::info(
        "capture",
        format!(
            "screenshots capture method=screenshots origin=({}, {}) size={}x{} black_ratio={:.3}",
            origin_x,
            origin_y,
            image.width(),
            image.height(),
            black_ratio
        ),
    );

    if black_ratio < 0.97 {
        return Ok(CapturedScreen {
            image,
            origin_x,
            origin_y,
            method: "screenshots",
        });
    }

    logger::error(
        "capture",
        "screenshots capture looks black, falling back to ScreenDC",
    );

    capture_screendc()
}

fn dark_pixel_ratio(image: &RgbaImage) -> f32 {
    let total = image.width().saturating_mul(image.height());
    if total == 0 {
        return 1.0;
    }

    let dark = image
        .pixels()
        .filter(|pixel| {
            let [r, g, b, _] = pixel.0;
            u16::from(r) + u16::from(g) + u16::from(b) < 24
        })
        .count();

    dark as f32 / total as f32
}

#[cfg(target_os = "windows")]
fn capture_screendc() -> Result<CapturedScreen, String> {
    use std::mem::size_of;
    use windows_sys::Win32::Graphics::Gdi::{
        BitBlt, CreateCompatibleBitmap, CreateCompatibleDC, DeleteDC, DeleteObject, GetDC,
        GetDIBits, ReleaseDC, SelectObject, BITMAPINFO, BITMAPINFOHEADER, BI_RGB, DIB_RGB_COLORS,
        HBITMAP, HDC, RGBQUAD, SRCCOPY,
    };
    use windows_sys::Win32::UI::WindowsAndMessaging::{
        GetSystemMetrics, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN, SM_XVIRTUALSCREEN,
        SM_YVIRTUALSCREEN,
    };

    unsafe {
        let origin_x = GetSystemMetrics(SM_XVIRTUALSCREEN);
        let origin_y = GetSystemMetrics(SM_YVIRTUALSCREEN);
        let width = GetSystemMetrics(SM_CXVIRTUALSCREEN);
        let height = GetSystemMetrics(SM_CYVIRTUALSCREEN);

        if width <= 0 || height <= 0 {
            return Err("ScreenDC virtual screen dimensions are invalid".to_string());
        }

        let screen_dc: HDC = GetDC(0);
        if screen_dc == 0 {
            return Err("ScreenDC GetDC failed".to_string());
        }

        let memory_dc: HDC = CreateCompatibleDC(screen_dc);
        if memory_dc == 0 {
            ReleaseDC(0, screen_dc);
            return Err("ScreenDC CreateCompatibleDC failed".to_string());
        }

        let bitmap: HBITMAP = CreateCompatibleBitmap(screen_dc, width, height);
        if bitmap == 0 {
            DeleteDC(memory_dc);
            ReleaseDC(0, screen_dc);
            return Err("ScreenDC CreateCompatibleBitmap failed".to_string());
        }

        let old_object = SelectObject(memory_dc, bitmap as isize);
        let bitblt_ok = BitBlt(
            memory_dc, 0, 0, width, height, screen_dc, origin_x, origin_y, SRCCOPY,
        );
        if bitblt_ok == 0 {
            SelectObject(memory_dc, old_object);
            DeleteObject(bitmap as isize);
            DeleteDC(memory_dc);
            ReleaseDC(0, screen_dc);
            return Err("ScreenDC BitBlt failed".to_string());
        }

        let mut bitmap_info = BITMAPINFO {
            bmiHeader: BITMAPINFOHEADER {
                biSize: size_of::<BITMAPINFOHEADER>() as u32,
                biWidth: width,
                biHeight: -height,
                biPlanes: 1,
                biBitCount: 32,
                biCompression: BI_RGB,
                biSizeImage: (width * height * 4) as u32,
                biXPelsPerMeter: 0,
                biYPelsPerMeter: 0,
                biClrUsed: 0,
                biClrImportant: 0,
            },
            bmiColors: [RGBQUAD {
                rgbBlue: 0,
                rgbGreen: 0,
                rgbRed: 0,
                rgbReserved: 0,
            }],
        };
        let mut bgra = vec![0u8; (width * height * 4) as usize];

        let scan_lines = GetDIBits(
            memory_dc,
            bitmap,
            0,
            height as u32,
            bgra.as_mut_ptr().cast(),
            &mut bitmap_info,
            DIB_RGB_COLORS,
        );

        SelectObject(memory_dc, old_object);
        DeleteObject(bitmap as isize);
        DeleteDC(memory_dc);
        ReleaseDC(0, screen_dc);

        if scan_lines == 0 {
            return Err("ScreenDC GetDIBits failed".to_string());
        }

        for pixel in bgra.chunks_exact_mut(4) {
            pixel.swap(0, 2);
            pixel[3] = 255;
        }

        let image = RgbaImage::from_raw(width as u32, height as u32, bgra)
            .ok_or("ScreenDC image buffer has invalid dimensions")?;
        let black_ratio = dark_pixel_ratio(&image);
        logger::info(
            "capture",
            format!(
                "screendc capture origin=({}, {}) size={}x{} black_ratio={:.3}",
                origin_x,
                origin_y,
                image.width(),
                image.height(),
                black_ratio
            ),
        );

        Ok(CapturedScreen {
            image,
            origin_x,
            origin_y,
            method: "screendc",
        })
    }
}

#[cfg(not(target_os = "windows"))]
fn capture_screendc() -> Result<CapturedScreen, String> {
    Err("ScreenDC fallback is only available on Windows".to_string())
}
