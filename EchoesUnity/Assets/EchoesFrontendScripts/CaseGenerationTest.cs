using UnityEngine;
using System.Collections;
using UnityEngine.Networking;
using System.Text;

public class CaseGenerationTest : MonoBehaviour
{
    private const string API_URL = "http://127.0.0.1:8000/api/cases/generate/";

    void Start()
    {
        StartCoroutine(GenerateCase());
    }

    private IEnumerator GenerateCase()
    {
        Debug.Log("Generating new case");
        using(UnityWebRequest request = new UnityWebRequest(API_URL, "POST"))
        {
            byte[] Body = Encoding.UTF8.GetBytes("{}");

            request.uploadHandler = new UploadHandlerRaw(Body);
            request.downloadHandler = new DownloadHandlerBuffer();

            request.SetRequestHeader("Content-Type","application/json");

            yield return request.SendWebRequest();

            if(request.result == UnityWebRequest.Result.Success)
            {
                Debug.Log("Case genearation successful");
                Debug.Log(request.downloadHandler.text);
            }
            else
            {
                Debug.LogError("Case generation failed"+request.error);
                Debug.LogError("Server response"+ request.downloadHandler.text);
            }
        }
    }
}
