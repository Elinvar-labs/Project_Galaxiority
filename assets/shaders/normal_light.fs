#version 330

in vec3 fragNormal;
in vec2 fragTexCoord;
in vec3 fragPos;

out vec4 color;

uniform sampler2D albedoMap;
uniform sampler2D normalMap;
uniform vec3 lightPos;
uniform vec3 viewPos;

void main() {
    // 1. Читаем текстуры
    vec3 albedo = texture(albedoMap, fragTexCoord).rgb;
    vec3 normal = texture(normalMap, fragTexCoord).rgb;

    // 2. Конвертируем нормаль из [0, 1] в [-1, 1]
    normal = normalize(normal * 2.0 - 1.0);

    // 3. Рассчитываем векторы света и взгляда (теперь правильно!)
    vec3 lightDir = normalize(lightPos - fragPos);
    vec3 viewDir = normalize(viewPos - fragPos);
    vec3 reflectDir = reflect(-lightDir, normal);

    // 4. Диффузное освещение (Lambert)
    float diff = max(dot(normal, lightDir), 0.0);
    vec3 diffuse = diff * albedo;

    // 5. Спекулярное освещение (Phong) - опционально, но делает картинку живее
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);
    vec3 specular = vec3(1.0) * spec;

    // Итоговый цвет
    color = vec4(diffuse + specular, 1.0);
}
